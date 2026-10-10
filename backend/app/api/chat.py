"""
Chat API: conversational RAG interface with streaming support.
"""
import uuid
from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.conversation import (
    Citation, Conversation, Message, MessageRole,
    ToolExecution, ToolStatus, UserFeedback
)
from app.models.user import User
from app.rag.pipeline import persist_rag_response, run_rag_pipeline

router = APIRouter()
logger = structlog.get_logger(__name__)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000)
    conversation_id: Optional[str] = None
    stream: bool = False
    top_k: Optional[int] = Field(default=None, ge=1, le=20)
    similarity_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class CitationOut(BaseModel):
    id: str
    document_name: Optional[str]
    page_number: Optional[int]
    section_title: Optional[str]
    passage: Optional[str]
    similarity_score: Optional[float]
    rank: int


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    citations: List[CitationOut] = []
    has_sufficient_evidence: Optional[bool]
    retrieval_latency_ms: Optional[float]
    generation_latency_ms: Optional[float]
    total_latency_ms: Optional[float]
    created_at: datetime


class ChatResponse(BaseModel):
    conversation_id: str
    message: MessageOut


class FeedbackRequest(BaseModel):
    message_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)


@router.post("/chat", response_model=ChatResponse, summary="Ask the AI assistant")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a question and receive a grounded answer with source citations.
    Creates or continues a conversation.
    """
    # Get or create conversation
    conversation_id = request.conversation_id
    if conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conv = Conversation(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            title=request.question[:80],
        )
        db.add(conv)
        await db.flush()
        conversation_id = conv.id

    # Persist user message
    user_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=request.question,
    )
    db.add(user_msg)
    await db.flush()

    # Run RAG pipeline
    try:
        rag_response = await run_rag_pipeline(
            question=request.question,
            db=db,
            conversation_id=conversation_id,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Persist assistant message
    assistant_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role=MessageRole.ASSISTANT,
        content=rag_response.answer,
        retrieval_latency_ms=rag_response.retrieval_latency_ms,
        generation_latency_ms=rag_response.generation_latency_ms,
        total_latency_ms=rag_response.total_latency_ms,
        prompt_version=rag_response.prompt_version,
        model_used=rag_response.model_used,
        has_sufficient_evidence=rag_response.has_sufficient_evidence,
    )
    db.add(assistant_msg)
    await db.flush()

    # Persist citations
    await persist_rag_response(rag_response, assistant_msg, db)

    # Load citations for response
    citations_result = await db.execute(
        select(Citation).where(Citation.message_id == assistant_msg.id).order_by(Citation.rank)
    )
    citations = citations_result.scalars().all()

    await db.commit()

    return ChatResponse(
        conversation_id=conversation_id,
        message=MessageOut(
            id=assistant_msg.id,
            role=assistant_msg.role.value,
            content=assistant_msg.content,
            citations=[
                CitationOut(
                    id=c.id,
                    document_name=c.document_name,
                    page_number=c.page_number,
                    section_title=c.section_title,
                    passage=c.passage,
                    similarity_score=c.similarity_score,
                    rank=c.rank,
                )
                for c in citations
            ],
            has_sufficient_evidence=assistant_msg.has_sufficient_evidence,
            retrieval_latency_ms=assistant_msg.retrieval_latency_ms,
            generation_latency_ms=assistant_msg.generation_latency_ms,
            total_latency_ms=assistant_msg.total_latency_ms,
            created_at=assistant_msg.created_at,
        ),
    )


@router.get("/conversations", summary="List conversations")
async def list_conversations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's conversations."""
    from sqlalchemy import func
    query = select(Conversation).where(Conversation.user_id == current_user.id)
    count = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count.scalar() or 0

    result = await db.execute(
        query.order_by(Conversation.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    convs = result.scalars().all()

    return {
        "items": [
            {
                "id": c.id,
                "title": c.title,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
            }
            for c in convs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/conversations/{conversation_id}", summary="Get conversation with messages")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()

    msgs_out = []
    for msg in messages:
        cit_result = await db.execute(
            select(Citation).where(Citation.message_id == msg.id).order_by(Citation.rank)
        )
        cits = cit_result.scalars().all()
        msgs_out.append({
            "id": msg.id,
            "role": msg.role.value,
            "content": msg.content,
            "has_sufficient_evidence": msg.has_sufficient_evidence,
            "total_latency_ms": msg.total_latency_ms,
            "created_at": msg.created_at,
            "citations": [
                {
                    "id": c.id,
                    "document_name": c.document_name,
                    "page_number": c.page_number,
                    "passage": c.passage,
                    "similarity_score": c.similarity_score,
                    "rank": c.rank,
                }
                for c in cits
            ],
        })

    return {"id": conv.id, "title": conv.title, "messages": msgs_out}


@router.post("/feedback", summary="Submit answer feedback")
async def submit_feedback(
    data: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a thumbs up/down rating for an assistant message."""
    result = await db.execute(select(Message).where(Message.id == data.message_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    feedback = UserFeedback(
        id=str(uuid.uuid4()),
        message_id=data.message_id,
        user_id=current_user.id,
        rating=data.rating,
        comment=data.comment,
    )
    db.add(feedback)
    await db.commit()
    return {"message": "Feedback recorded", "feedback_id": feedback.id}
