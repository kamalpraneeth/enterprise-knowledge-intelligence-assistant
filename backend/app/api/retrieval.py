import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.conversation import AuditEvent
from app.models.user import User
from app.rag.retrieval import retrieve_similar_chunks

router = APIRouter()


class RetrievalRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    document_ids: Optional[List[str]] = None


class RetrievalResult(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: Optional[int]
    section_title: Optional[str]
    content: str
    similarity_score: float


class RetrievalResponse(BaseModel):
    results: List[RetrievalResult]
    total: int
    latency_ms: float


@router.post("/search", response_model=RetrievalResponse, summary="Semantic search")
@limiter.limit("60/minute")
async def search(
    request: Request,
    body: RetrievalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Perform semantic search over the indexed knowledge base and audit-log the query."""
    chunks, latency_ms = await retrieve_similar_chunks(
        query=body.query,
        db=db,
        top_k=body.top_k,
        similarity_threshold=body.similarity_threshold,
        document_ids=body.document_ids,
    )

    # Audit log document search event without logging raw sensitive PII
    try:
        audit = AuditEvent(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            event_type="document_query",
            resource_type="knowledge_base",
            resource_id="semantic_search",
            details={
                "query_length": len(body.query),
                "top_k": body.top_k,
                "chunks_found": len(chunks),
                "latency_ms": round(latency_ms, 2),
            },
            ip_address=request.client.host if request.client else None,
        )
        db.add(audit)
        await db.commit()
    except Exception as e:
        pass
    return RetrievalResponse(
        results=[
            RetrievalResult(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                document_name=c.document_name,
                page_number=c.page_number,
                section_title=c.section_title,
                content=c.content,
                similarity_score=c.similarity_score,
            )
            for c in chunks
        ],
        total=len(chunks),
        latency_ms=round(latency_ms, 2),
    )
