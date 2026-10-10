"""
Controlled tool definitions for agentic AI.
All tools:
- Have typed input/output schemas
- Enforce read-only database access via parameterized queries
- Cannot execute arbitrary SQL or shell commands
- Log all executions
"""
import time
import uuid
from typing import Any, Dict, List, Optional

import structlog
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.rag.retrieval import retrieve_similar_chunks

logger = structlog.get_logger(__name__)

MAX_TOOL_CALLS_PER_REQUEST = 5


# ── Tool Input/Output Schemas ─────────────────────────────────────────────────

class SearchKBInput(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    top_k: Optional[int] = Field(default=5, ge=1, le=20)
    document_ids: Optional[List[str]] = Field(default=None)


class SearchKBOutput(BaseModel):
    results: List[Dict[str, Any]]
    total_found: int


class GetDocumentMetadataInput(BaseModel):
    document_id: str = Field(..., min_length=1, max_length=36)


class GetDocumentMetadataOutput(BaseModel):
    id: str
    original_filename: str
    file_type: str
    status: str
    page_count: Optional[int]
    chunk_count: Optional[int]
    indexed_at: Optional[str]


class LookupPolicyRecordInput(BaseModel):
    policy_id: str = Field(..., pattern=r"^[a-zA-Z0-9\-_]{1,50}$")


class LookupPolicyRecordOutput(BaseModel):
    found: bool
    policy_id: str
    data: Optional[Dict[str, Any]]


class CreateSupportRequestInput(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    confirmed: bool = Field(..., description="Must be True — user explicitly confirmed")


class CreateSupportRequestOutput(BaseModel):
    ticket_id: str
    status: str
    message: str


# ── Tool Implementations ──────────────────────────────────────────────────────

class ToolResult(BaseModel):
    tool_name: str
    status: str  # "success" | "error" | "skipped"
    output: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    error_category: Optional[str] = None


async def search_knowledge_base(
    args: SearchKBInput, db: AsyncSession
) -> ToolResult:
    """Semantic search over the knowledge base."""
    start = time.time()
    try:
        chunks, _ = await retrieve_similar_chunks(
            query=args.query,
            db=db,
            top_k=args.top_k,
            document_ids=args.document_ids,
        )
        output = SearchKBOutput(
            results=[
                {
                    "chunk_id": c.chunk_id,
                    "document_name": c.document_name,
                    "page_number": c.page_number,
                    "content": c.content[:500],
                    "similarity": c.similarity_score,
                }
                for c in chunks
            ],
            total_found=len(chunks),
        )
        return ToolResult(
            tool_name="search_knowledge_base",
            status="success",
            output=output.model_dump(),
            duration_ms=(time.time() - start) * 1000,
        )
    except Exception as e:
        logger.error("search_knowledge_base failed", error=str(e))
        return ToolResult(
            tool_name="search_knowledge_base",
            status="error",
            error=str(e),
            error_category="retrieval_error",
            duration_ms=(time.time() - start) * 1000,
        )


async def get_document_metadata(
    args: GetDocumentMetadataInput, db: AsyncSession
) -> ToolResult:
    """Read-only document metadata lookup."""
    start = time.time()
    try:
        result = await db.execute(
            select(Document).where(Document.id == args.document_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return ToolResult(
                tool_name="get_document_metadata",
                status="error",
                error=f"Document {args.document_id} not found",
                error_category="not_found",
                duration_ms=(time.time() - start) * 1000,
            )
        output = GetDocumentMetadataOutput(
            id=doc.id,
            original_filename=doc.original_filename,
            file_type=doc.file_type,
            status=doc.status.value,
            page_count=doc.page_count,
            chunk_count=doc.chunk_count,
            indexed_at=doc.indexed_at.isoformat() if doc.indexed_at else None,
        )
        return ToolResult(
            tool_name="get_document_metadata",
            status="success",
            output=output.model_dump(),
            duration_ms=(time.time() - start) * 1000,
        )
    except Exception as e:
        return ToolResult(
            tool_name="get_document_metadata",
            status="error",
            error=str(e),
            error_category="database_error",
            duration_ms=(time.time() - start) * 1000,
        )


async def lookup_policy_record(
    args: LookupPolicyRecordInput, db: AsyncSession
) -> ToolResult:
    """
    Read-only parameterized SQL lookup of policy records.
    Only approved, safe column names are selected — no arbitrary SQL execution.
    """
    start = time.time()
    try:
        # Parameterized query — policy_id is from validated schema (alphanumeric only)
        result = await db.execute(
            text("""
                SELECT id, original_filename as policy_name, file_type, status, indexed_at
                FROM documents
                WHERE id = :policy_id
                AND status = 'indexed'
                LIMIT 1
            """),
            {"policy_id": args.policy_id},
        )
        row = result.fetchone()
        if not row:
            return ToolResult(
                tool_name="lookup_policy_record",
                status="success",
                output=LookupPolicyRecordOutput(
                    found=False, policy_id=args.policy_id, data=None
                ).model_dump(),
                duration_ms=(time.time() - start) * 1000,
            )
        return ToolResult(
            tool_name="lookup_policy_record",
            status="success",
            output=LookupPolicyRecordOutput(
                found=True,
                policy_id=args.policy_id,
                data={
                    "policy_name": row.policy_name,
                    "file_type": row.file_type,
                    "status": row.status,
                    "indexed_at": str(row.indexed_at) if row.indexed_at else None,
                },
            ).model_dump(),
            duration_ms=(time.time() - start) * 1000,
        )
    except Exception as e:
        return ToolResult(
            tool_name="lookup_policy_record",
            status="error",
            error=str(e),
            error_category="database_error",
            duration_ms=(time.time() - start) * 1000,
        )


async def create_support_request(
    args: CreateSupportRequestInput, db: AsyncSession
) -> ToolResult:
    """
    Create a support ticket. Requires explicit user confirmation.
    """
    start = time.time()
    if not args.confirmed:
        return ToolResult(
            tool_name="create_support_request",
            status="skipped",
            error="User confirmation required before creating a support request.",
            error_category="confirmation_required",
            duration_ms=(time.time() - start) * 1000,
        )
    ticket_id = f"TICKET-{str(uuid.uuid4())[:8].upper()}"
    return ToolResult(
        tool_name="create_support_request",
        status="success",
        output=CreateSupportRequestOutput(
            ticket_id=ticket_id,
            status="created",
            message=f"Support request '{args.title}' submitted. Ticket ID: {ticket_id}",
        ).model_dump(),
        duration_ms=(time.time() - start) * 1000,
    )


# Tool registry
TOOL_REGISTRY = {
    "search_knowledge_base": (search_knowledge_base, SearchKBInput),
    "get_document_metadata": (get_document_metadata, GetDocumentMetadataInput),
    "lookup_policy_record": (lookup_policy_record, LookupPolicyRecordInput),
    "create_support_request": (create_support_request, CreateSupportRequestInput),
}


async def execute_tool(
    tool_name: str,
    raw_args: dict,
    db: AsyncSession,
) -> ToolResult:
    """
    Execute a named tool with validated arguments.
    Enforces allowlist, argument validation, and error handling.
    """
    if tool_name not in TOOL_REGISTRY:
        return ToolResult(
            tool_name=tool_name,
            status="error",
            error=f"Tool '{tool_name}' is not available",
            error_category="not_found",
        )

    fn, schema = TOOL_REGISTRY[tool_name]
    try:
        validated_args = schema(**raw_args)
    except Exception as e:
        return ToolResult(
            tool_name=tool_name,
            status="error",
            error=f"Invalid arguments: {str(e)}",
            error_category="validation_error",
        )

    logger.info("Executing tool", tool_name=tool_name)
    result = await fn(validated_args, db)
    logger.info(
        "Tool executed",
        tool_name=tool_name,
        status=result.status,
        duration_ms=round(result.duration_ms),
    )
    return result
