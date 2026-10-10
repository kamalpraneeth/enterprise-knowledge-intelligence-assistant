"""
Tests for RAG pipeline components.
Uses fake LLM and embedding providers.
"""
import pytest
from app.rag.prompts import (
    format_context,
    RetrievedChunk,
    INSUFFICIENT_EVIDENCE_RESPONSE,
    PROMPT_VERSION,
)
from app.rag.pipeline import validate_citations
from app.services.llm import FakeLLMProvider


def make_chunk(n: int) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"chunk-{n}",
        document_id=f"doc-{n}",
        document_name=f"Policy_{n}.pdf",
        page_number=n,
        section_title=f"Section {n}",
        content=f"This is the content of chunk {n}.",
        similarity_score=0.9 - n * 0.05,
    )


def test_format_context_single_chunk():
    """format_context produces readable source block."""
    chunk = make_chunk(1)
    context = format_context([chunk])
    assert "[Source 1]" in context
    assert "Policy_1.pdf" in context
    assert "Page 1" in context


def test_format_context_multiple_chunks():
    """Multiple chunks are separated with dividers."""
    chunks = [make_chunk(i) for i in range(1, 4)]
    context = format_context(chunks)
    assert "[Source 1]" in context
    assert "[Source 2]" in context
    assert "[Source 3]" in context


def test_validate_citations_extracts_correct_sources():
    """Citations matching [Source N] in answer are returned."""
    chunks = [make_chunk(1), make_chunk(2), make_chunk(3)]
    answer = "According to [Source 1] and [Source 3], the policy applies."
    _, cited = validate_citations(answer, chunks)
    assert len(cited) == 2
    cited_ids = [c.chunk_id for c in cited]
    assert "chunk-1" in cited_ids
    assert "chunk-3" in cited_ids
    assert "chunk-2" not in cited_ids


def test_validate_citations_no_references():
    """No [Source N] references means no citations."""
    chunks = [make_chunk(1)]
    answer = "The policy states that employees should follow procedures."
    _, cited = validate_citations(answer, chunks)
    assert cited == []


def test_validate_citations_out_of_range():
    """Citation number beyond chunk count is ignored."""
    chunks = [make_chunk(1)]
    answer = "See [Source 5] for details."
    _, cited = validate_citations(answer, chunks)
    assert cited == []


@pytest.mark.asyncio
async def test_fake_llm_sufficient_evidence():
    """Fake LLM returns structured answer for normal queries."""
    llm = FakeLLMProvider()
    response = await llm.generate("What is the leave policy?")
    assert len(response) > 0
    assert isinstance(response, str)


@pytest.mark.asyncio
async def test_fake_llm_insufficient_evidence():
    """Fake LLM correctly handles insufficient evidence prompts."""
    llm = FakeLLMProvider()
    response = await llm.generate("cannot determine the answer from available documents")
    assert "cannot determine" in response.lower()


def test_prompt_version_is_set():
    """PROMPT_VERSION is a non-empty string."""
    assert PROMPT_VERSION
    assert isinstance(PROMPT_VERSION, str)
    assert len(PROMPT_VERSION) > 0


def test_insufficient_evidence_response_is_safe():
    """Insufficient evidence message is user-safe."""
    assert "cannot determine" in INSUFFICIENT_EVIDENCE_RESPONSE.lower()
    assert "API_KEY" not in INSUFFICIENT_EVIDENCE_RESPONSE
    assert "traceback" not in INSUFFICIENT_EVIDENCE_RESPONSE.lower()
