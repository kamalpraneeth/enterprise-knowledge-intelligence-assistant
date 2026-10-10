"""
Document management API.
Upload, list, get, reindex, delete documents.
Restricted to admin/knowledge-manager for mutations.
"""
import asyncio
import uuid
from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_knowledge_manager
from app.db.session import get_db
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.services.ingestion import ingest_document, save_upload, validate_upload

router = APIRouter()
logger = structlog.get_logger(__name__)


class DocumentResponse(BaseModel):
    id: str
    original_filename: str
    file_type: str
    file_size_bytes: int
    title: Optional[str]
    status: str
    page_count: Optional[int]
    chunk_count: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    indexed_at: Optional[datetime]

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=201,
    summary="Upload a document",
)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    description: Optional[str] = None,
    current_user: User = Depends(require_knowledge_manager()),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a PDF, TXT, or DOCX document and trigger background ingestion.
    Only Knowledge Managers and Admins can upload.
    """
    # Read file content
    content = await file.read()

    # Validate
    try:
        await validate_upload(file.filename or "unknown", file.content_type or "", len(content))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    ext = (file.filename or "").rsplit(".", 1)[-1].lower()

    # Save to disk
    stored_filename = await save_upload(file.filename or "document", content)

    # Create document record
    doc = Document(
        id=str(uuid.uuid4()),
        filename=stored_filename,
        original_filename=file.filename or stored_filename,
        file_type=ext,
        file_size_bytes=len(content),
        title=title,
        description=description,
        status=DocumentStatus.PENDING,
        uploaded_by=current_user.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    logger.info("Document uploaded", document_id=doc.id, filename=doc.original_filename)

    # Trigger ingestion asynchronously (fire-and-forget for now)
    asyncio.create_task(_run_ingestion(doc.id))

    return DocumentResponse(
        id=doc.id,
        original_filename=doc.original_filename,
        file_type=doc.file_type,
        file_size_bytes=doc.file_size_bytes,
        title=doc.title,
        status=doc.status.value,
        page_count=doc.page_count,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
        created_at=doc.created_at,
        indexed_at=doc.indexed_at,
    )


async def _run_ingestion(document_id: str):
    """Run ingestion in a separate DB session."""
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await ingest_document(document_id, db)


@router.get("/", response_model=DocumentListResponse, summary="List documents")
async def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    search: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all documents with pagination and optional filters."""
    query = select(Document).where(Document.status != DocumentStatus.DELETED)

    if status_filter:
        try:
            query = query.where(Document.status == DocumentStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status: {status_filter}")

    if search:
        query = query.where(Document.original_filename.ilike(f"%{search}%"))

    # Count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    # Paginate
    query = query.order_by(Document.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    docs = result.scalars().all()

    return DocumentListResponse(
        items=[
            DocumentResponse(
                id=d.id,
                original_filename=d.original_filename,
                file_type=d.file_type,
                file_size_bytes=d.file_size_bytes,
                title=d.title,
                status=d.status.value,
                page_count=d.page_count,
                chunk_count=d.chunk_count,
                error_message=d.error_message,
                created_at=d.created_at,
                indexed_at=d.indexed_at,
            )
            for d in docs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=DocumentResponse, summary="Get document")
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc or doc.status == DocumentStatus.DELETED:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse(
        id=doc.id,
        original_filename=doc.original_filename,
        file_type=doc.file_type,
        file_size_bytes=doc.file_size_bytes,
        title=doc.title,
        status=doc.status.value,
        page_count=doc.page_count,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
        created_at=doc.created_at,
        indexed_at=doc.indexed_at,
    )


@router.post("/{document_id}/reindex", summary="Re-index document")
async def reindex_document(
    document_id: str,
    current_user: User = Depends(require_knowledge_manager()),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc or doc.status == DocumentStatus.DELETED:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.status = DocumentStatus.PENDING
    await db.commit()

    asyncio.create_task(_run_ingestion(document_id))
    logger.info("Reindex triggered", document_id=document_id)
    return {"message": "Re-indexing started", "document_id": document_id}


@router.delete("/{document_id}", status_code=204, summary="Delete document")
async def delete_document(
    document_id: str,
    current_user: User = Depends(require_knowledge_manager()),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete document and hard-delete associated chunks/embeddings."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Hard delete chunks (cascade removes embeddings)
    from sqlalchemy import delete
    await db.execute(
        delete(doc.chunks.__class__).where(
            doc.chunks.__class__.document_id == document_id
        )
    )

    # Soft delete document record
    doc.status = DocumentStatus.DELETED
    await db.commit()
    logger.info("Document deleted", document_id=document_id, user_id=current_user.id)
