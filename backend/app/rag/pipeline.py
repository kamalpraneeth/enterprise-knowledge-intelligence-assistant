"""
Complete RAG pipeline: retrieval → context construction → LLM generation → citation validation.
"""
import re
import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation import (
    Citation, Message, MessageRole
)
from app.rag.prompts import (
    QA_SYSTEM_PROMPT,
    INSUFFICIENT_EVIDENCE_RESPONSE,
    PROMPT_VERSION,
    RetrievedChunk,
    format_context,
)
from app.rag.retrieval import retrieve_similar_chunks
from app.services.llm import llm_service

logger = structlog.get_logger(__name__)


class RAGResponse:
    """Structured response from the RAG pipeline."""

    def __init__(
        self,
        answer: str,
        citations: List[RetrievedChunk],
        has_sufficient_evidence: bool,
        retrieval_latency_ms: float,
        generation_latency_ms: float,
        prompt_version: str,
        model_used: str,
    ):
        self.answer = answer
        self.citations = citations
        self.has_sufficient_evidence = has_sufficient_evidence
        self.retrieval_latency_ms = retrieval_latency_ms
        self.generation_latency_ms = generation_latency_ms
        self.total_latency_ms = retrieval_latency_ms + generation_latency_ms
        self.prompt_version = prompt_version
        self.model_used = model_used


async def run_rag_pipeline(
    question: str,
    db: AsyncSession,
    conversation_id: str,
    top_k: Optional[int] = None,
    similarity_threshold: Optional[float] = None,
    document_ids: Optional[List[str]] = None,
) -> RAGResponse:
    """
    Execute the full RAG pipeline.
    
    Flow: input validation → embedding → retrieval → context → LLM → citations → response
    """
    log = logger.bind(conversation_id=conversation_id, question_len=len(question))

    # 1. Input validation
    question = question.strip()
    if not question:
        raise ValueError("Question cannot be empty")
    if len(question) > 5000:
        raise ValueError("Question exceeds maximum length of 5000 characters")

    # 2. Retrieve relevant chunks
    chunks, retrieval_latency_ms = await retrieve_similar_chunks(
        query=question,
        db=db,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        document_ids=document_ids,
    )
    log.info("Chunks retrieved", count=len(chunks))

    # 3. Determine evidence sufficiency
    has_sufficient_evidence = len(chunks) > 0

    if not has_sufficient_evidence:
        log.info("Insufficient evidence — returning standard response")
        return RAGResponse(
            answer=INSUFFICIENT_EVIDENCE_RESPONSE,
            citations=[],
            has_sufficient_evidence=False,
            retrieval_latency_ms=retrieval_latency_ms,
            generation_latency_ms=0.0,
            prompt_version=PROMPT_VERSION,
            model_used=settings.LLM_MODEL,
        )

    # 4. Build context (limit to top_k)
    context_chunks = chunks[: top_k or settings.TOP_K_RETRIEVAL]
    context = format_context(context_chunks)

    # 5. Build prompt
    prompt = QA_SYSTEM_PROMPT.format(context=context, question=question)

    # 6. Generate answer
    gen_start = time.time()
    llm = llm_service()
    try:
        raw_answer = await llm.generate(prompt)
    except Exception as e:
        log.error("LLM generation error", error=str(e))
        raise RuntimeError(f"Answer generation failed: {str(e)}")
    generation_latency_ms = (time.time() - gen_start) * 1000

    # 7. Validate citations — ensure only referenced sources are cited
    validated_answer, cited_chunks = validate_citations(raw_answer, context_chunks)

    log.info(
        "RAG pipeline complete",
        retrieval_ms=round(retrieval_latency_ms),
        generation_ms=round(generation_latency_ms),
        cited_sources=len(cited_chunks),
    )

    return RAGResponse(
        answer=validated_answer,
        citations=cited_chunks,
        has_sufficient_evidence=True,
        retrieval_latency_ms=retrieval_latency_ms,
        generation_latency_ms=generation_latency_ms,
        prompt_version=PROMPT_VERSION,
        model_used=settings.LLM_MODEL,
    )


def validate_citations(answer: str, chunks: List[RetrievedChunk]) -> Tuple[str, List[RetrievedChunk]]:
    """
    Identify which source references (e.g. [Source 1]) appear in the answer
    and return only those chunks. Prevents fabricated citation numbers.
    """
    referenced_numbers = set(re.findall(r"\[Source (\d+)\]", answer))
    cited = []
    for idx_str in referenced_numbers:
        idx = int(idx_str) - 1
        if 0 <= idx < len(chunks):
            cited.append(chunks[idx])

    # If no valid citations found but answer is not the insufficient-evidence message,
    # keep all retrieved chunks as potential context but don't mark them as cited
    if not cited and INSUFFICIENT_EVIDENCE_RESPONSE not in answer:
        cited = []

    return answer, cited


async def persist_rag_response(
    response: RAGResponse,
    message: Message,
    db: AsyncSession,
) -> None:
    """Save citations linked to the assistant message."""
    for rank, chunk in enumerate(response.citations, 1):
        citation = Citation(
            id=str(uuid.uuid4()),
            message_id=message.id,
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            document_name=chunk.document_name,
            page_number=chunk.page_number,
            section_title=chunk.section_title,
            passage=chunk.content[:1000],  # Limit stored passage length
            similarity_score=chunk.similarity_score,
            rank=rank,
        )
        db.add(citation)
    await db.commit()
