"""
Document ingestion pipeline.
Handles PDF, TXT, DOCX text extraction, chunking, embedding, and vector storage.
Treats uploaded file content as untrusted — document instructions never override system prompts.
"""
import asyncio
import hashlib
import io
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple, Optional

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.services.embedding import embedding_service

logger = structlog.get_logger(__name__)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# ── Text Extraction ──────────────────────────────────────────────────────────

def extract_text_pdf(file_bytes: bytes) -> Tuple[str, int]:
    """Extract text and page count from PDF bytes."""
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    full_text = "\n\n".join(pages)
    return full_text, len(reader.pages)


def extract_text_docx(file_bytes: bytes) -> Tuple[str, int]:
    """Extract text from DOCX bytes."""
    from docx import Document as DocxDocument
    doc = DocxDocument(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs), 1


def extract_text_txt(file_bytes: bytes) -> Tuple[str, int]:
    """Decode TXT bytes."""
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1", errors="replace")
    return text, 1


def extract_text(file_bytes: bytes, file_type: str) -> Tuple[str, int]:
    """Dispatch text extraction by file type."""
    extractors = {
        "pdf": extract_text_pdf,
        "docx": extract_text_docx,
        "txt": extract_text_txt,
    }
    extractor = extractors.get(file_type.lower())
    if not extractor:
        raise ValueError(f"Unsupported file type: {file_type}")
    text, pages = extractor(file_bytes)
    return normalize_text(text), pages


def normalize_text(text: str) -> str:
    """Normalize whitespace and remove non-printable characters."""
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_text(
    text: str,
    chunk_size: int = None,
    overlap: int = None,
) -> List[dict]:
    """
    Split text into overlapping chunks by word count.
    Returns list of dicts with 'content', 'chunk_index', 'page_number' (estimated).
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP

    words = text.split()
    chunks = []
    start = 0
    idx = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunk_content = " ".join(chunk_words)

        if chunk_content.strip():
            # Estimate page number based on word position
            approx_page = max(1, (start // (chunk_size * 2)) + 1)
            chunks.append({
                "content": chunk_content,
                "chunk_index": idx,
                "page_number": approx_page,
                "token_count": len(chunk_words),
            })
            idx += 1

        if end >= len(words):
            break
        start += chunk_size - overlap

    return chunks


# ── Ingestion Pipeline ────────────────────────────────────────────────────────

async def ingest_document(document_id: str, db: AsyncSession) -> None:
    """
    Full ingestion pipeline for a document.
    1. Load document record and file.
    2. Extract text.
    3. Chunk text.
    4. Generate embeddings.
    5. Store chunks + embeddings.
    6. Update document status.
    
    This function is idempotent — re-running deletes previous chunks first.
    """
    start_time = time.time()
    log = logger.bind(document_id=document_id)

    # Load document
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        log.error("Document not found for ingestion")
        return

    # Mark as processing
    doc.status = DocumentStatus.PROCESSING
    await db.commit()
    log.info("Starting document ingestion", filename=doc.filename)

    try:
        # Load file bytes
        file_path = UPLOAD_DIR / doc.filename
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_bytes = file_path.read_bytes()

        # Extract text
        text, page_count = await asyncio.to_thread(extract_text, file_bytes, doc.file_type)

        if not text.strip():
            raise ValueError("Document contains no extractable text")

        doc.page_count = page_count

        # Delete existing chunks (re-indexing case)
        from sqlalchemy import delete
        await db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )

        # Chunk text
        chunks_data = chunk_text(text)
        log.info("Chunking complete", chunk_count=len(chunks_data))

        if not chunks_data:
            raise ValueError("No chunks generated from document")

        # Generate embeddings in batch
        embedder = embedding_service()
        texts_to_embed = [c["content"] for c in chunks_data]
        embeddings = await embedder.embed_batch(texts_to_embed)
        log.info("Embeddings generated", count=len(embeddings))

        # Store chunks
        chunk_objects = []
        for i, (chunk_data, embedding) in enumerate(zip(chunks_data, embeddings)):
            chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                document_id=document_id,
                chunk_index=chunk_data["chunk_index"],
                content=chunk_data["content"],
                page_number=chunk_data.get("page_number"),
                token_count=chunk_data.get("token_count"),
                embedding=embedding,
            )
            chunk_objects.append(chunk)

        db.add_all(chunk_objects)

        # Update document to indexed
        doc.status = DocumentStatus.INDEXED
        doc.chunk_count = len(chunk_objects)
        doc.indexed_at = datetime.now(timezone.utc)
        doc.error_message = None
        await db.commit()

        elapsed_ms = (time.time() - start_time) * 1000
        log.info(
            "Document indexed successfully",
            chunk_count=len(chunk_objects),
            page_count=page_count,
            elapsed_ms=round(elapsed_ms),
        )

    except Exception as e:
        await db.rollback()
        log.error("Document ingestion failed", error=str(e))
        # Mark as failed — reload to avoid stale state
        result = await db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if doc:
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)[:500]
            await db.commit()


async def validate_upload(filename: str, content_type: str, size: int) -> None:
    """Validate file before saving."""
    ext = Path(filename).suffix.lstrip(".").lower()
    if ext not in settings.allowed_extensions_list:
        raise ValueError(
            f"File type '{ext}' not supported. Allowed: {settings.allowed_extensions_list}"
        )
    if size > settings.max_file_size_bytes:
        raise ValueError(
            f"File size {size / 1024 / 1024:.1f} MB exceeds limit of {settings.MAX_FILE_SIZE_MB} MB"
        )


async def save_upload(filename: str, content: bytes) -> str:
    """
    Save uploaded file to disk with a UUID-prefixed name.
    Returns the stored filename.
    """
    ext = Path(filename).suffix.lower()
    safe_name = f"{uuid.uuid4()}{ext}"
    dest = UPLOAD_DIR / safe_name
    await asyncio.to_thread(dest.write_bytes, content)
    return safe_name
