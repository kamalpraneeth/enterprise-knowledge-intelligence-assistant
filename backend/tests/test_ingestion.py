"""
Tests for document ingestion pipeline.
Uses fake embedding provider — no API calls required.
"""
import io
import pytest
from unittest.mock import patch, AsyncMock

from app.services.ingestion import (
    chunk_text,
    extract_text_txt,
    normalize_text,
    validate_upload,
)
from app.services.embedding import FakeEmbeddingProvider


@pytest.mark.asyncio
async def test_validate_upload_valid_txt():
    """Valid TXT file passes validation."""
    await validate_upload("test.txt", "text/plain", 100)


@pytest.mark.asyncio
async def test_validate_upload_invalid_extension():
    """Unsupported file type raises ValueError."""
    with pytest.raises(ValueError, match="not supported"):
        await validate_upload("test.exe", "application/octet-stream", 100)


@pytest.mark.asyncio
async def test_validate_upload_too_large():
    """File exceeding size limit raises ValueError."""
    with pytest.raises(ValueError, match="exceeds limit"):
        await validate_upload("test.txt", "text/plain", 60 * 1024 * 1024)


def test_extract_text_txt_utf8():
    """TXT extraction decodes UTF-8 content."""
    content = "Hello, world! This is a test document."
    text, pages = extract_text_txt(content.encode("utf-8"))
    assert "Hello" in text
    assert pages == 1


def test_normalize_text_removes_extra_whitespace():
    """Text normalization removes redundant whitespace."""
    text = "Hello   world\r\n\nThis   is   a   test\n\n\n"
    result = normalize_text(text)
    assert "   " not in result
    assert result.strip() == result


def test_chunk_text_basic():
    """Chunking produces expected number of chunks."""
    text = " ".join([f"word{i}" for i in range(100)])
    chunks = chunk_text(text, chunk_size=20, overlap=5)
    assert len(chunks) > 1
    for chunk in chunks:
        assert "content" in chunk
        assert "chunk_index" in chunk
        assert len(chunk["content"]) > 0


def test_chunk_text_empty():
    """Empty text produces no chunks."""
    chunks = chunk_text("", chunk_size=20, overlap=5)
    assert chunks == []


def test_chunk_text_single_chunk():
    """Short text fits in a single chunk."""
    text = "This is a short document."
    chunks = chunk_text(text, chunk_size=100, overlap=10)
    assert len(chunks) == 1
    assert chunks[0]["chunk_index"] == 0


def test_chunk_text_overlap():
    """Chunks overlap correctly."""
    text = " ".join([f"w{i}" for i in range(50)])
    chunks = chunk_text(text, chunk_size=20, overlap=5)
    # Check that consecutive chunks share some words
    if len(chunks) >= 2:
        words0 = set(chunks[0]["content"].split())
        words1 = set(chunks[1]["content"].split())
        # With overlap=5, some words should be shared
        assert len(words0 & words1) > 0


@pytest.mark.asyncio
async def test_fake_embedding_consistency():
    """Fake embeddings are deterministic and normalized."""
    provider = FakeEmbeddingProvider(dim=768)
    emb1 = await provider.embed_text("hello world")
    emb2 = await provider.embed_text("hello world")
    assert emb1 == emb2
    assert len(emb1) == 768
    # Should be normalized (magnitude ≈ 1)
    magnitude = sum(x**2 for x in emb1) ** 0.5
    assert abs(magnitude - 1.0) < 0.01


@pytest.mark.asyncio
async def test_fake_embedding_different_texts():
    """Different texts produce different embeddings."""
    provider = FakeEmbeddingProvider(dim=768)
    emb1 = await provider.embed_text("hello world")
    emb2 = await provider.embed_text("completely different content")
    assert emb1 != emb2


@pytest.mark.asyncio
async def test_fake_embedding_batch():
    """Batch embedding returns list of embeddings."""
    provider = FakeEmbeddingProvider(dim=768)
    texts = ["text one", "text two", "text three"]
    embeddings = await provider.embed_batch(texts)
    assert len(embeddings) == 3
    for emb in embeddings:
        assert len(emb) == 768
