"""
Tool execution API — authenticated, allowlisted tool calling with audit logging.
"""
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.conversation import AuditEvent
from app.models.user import User
from app.tools.tools import TOOL_REGISTRY, execute_tool

router = APIRouter()
logger = structlog.get_logger(__name__)


class ToolExecuteRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]


class ToolExecuteResponse(BaseModel):
    tool_name: str
    status: str
    output: Optional[Any]
    error: Optional[str]
    duration_ms: float


@router.post("/execute", response_model=ToolExecuteResponse, summary="Execute a tool")
@limiter.limit("60/minute")
async def execute(
    request: Request,
    body: ToolExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute an approved tool with validated arguments.
    Only tools in the registry can be called. Audit-logs every execution.
    """
    if body.tool_name not in TOOL_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{body.tool_name}' not found. Available: {list(TOOL_REGISTRY.keys())}",
        )

    result = await execute_tool(
        tool_name=body.tool_name,
        raw_args=body.arguments,
        db=db,
    )

    # Sanitize input arguments to prevent recording raw tokens, credentials, or PII
    sanitized_args = {
        k: ("***" if any(sec in k.lower() for sec in ["token", "secret", "password", "key", "auth"]) else v)
        for k, v in body.arguments.items()
    }

    try:
        audit = AuditEvent(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            event_type="tool_execution",
            resource_type="tool",
            resource_id=body.tool_name,
            details={
                "tool_name": body.tool_name,
                "status": result.status,
                "duration_ms": round(result.duration_ms, 2),
                "error": result.error,
                "arguments": sanitized_args,
            },
            ip_address=request.client.host if request.client else None,
        )
        db.add(audit)
        await db.commit()
    except Exception as e:
        logger.error("Failed to write tool execution audit event", error=str(e))

    logger.info(
        "Tool API execution",
        user_id=current_user.id,
        tool_name=body.tool_name,
        status=result.status,
    )

    return ToolExecuteResponse(
        tool_name=result.tool_name,
        status=result.status,
        output=result.output,
        error=result.error,
        duration_ms=round(result.duration_ms, 2),
    )


@router.get("/available", summary="List available tools")
async def list_tools(current_user: User = Depends(get_current_user)):
    """Return available tool names and descriptions."""
    return {
        "tools": [
            {"name": "search_knowledge_base", "description": "Search documents by semantic similarity"},
            {"name": "get_document_metadata", "description": "Get metadata for a specific document"},
            {"name": "lookup_policy_record", "description": "Read-only lookup of policy records"},
            {"name": "create_support_request", "description": "Create a support request (requires confirmation)"},
        ]
    }
