"""
Vector retrieval service using pgvector cosine similarity search.
"""
import time
from typing import List, Optional

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.rag.prompts import RetrievedChunk
from app.services.embedding import embedding_service

logger = structlog.get_logger(__name__)


async def retrieve_similar_chunks(
    query: str,
    db: AsyncSession,
    top_k: Optional[int] = None,
    similarity_threshold: Optional[float] = None,
    document_ids: Optional[List[str]] = None,
) -> tuple[List[RetrievedChunk], float]:
    """
    Retrieve semantically similar chunks from pgvector.
    Returns (chunks, retrieval_latency_ms).
    """
    top_k = top_k or settings.TOP_K_RETRIEVAL
    threshold = similarity_threshold if similarity_threshold is not None else settings.SIMILARITY_THRESHOLD

    start = time.time()

    # Embed query
    embedder = embedding_service()
    query_embedding = await embedder.embed_text(query)

    # Build parameterized SQL for vector similarity search
    # Using cosine distance (1 - cosine_similarity)
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    filter_clause = ""
    params = {
        "embedding": embedding_str,
        "top_k": top_k,
        "threshold": 1.0 - threshold,  # pgvector uses distance not similarity
    }

    if document_ids:
        filter_clause = "AND dc.document_id = ANY(:doc_ids)"
        params["doc_ids"] = document_ids

    sql = text(f"""
        SELECT
            dc.id as chunk_id,
            dc.document_id,
            dc.content,
            dc.page_number,
            dc.section_title,
            d.original_filename as document_name,
            (dc.embedding <=> :embedding::vector) as distance
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE d.status = 'indexed'
        AND dc.embedding IS NOT NULL
        {filter_clause}
        AND (dc.embedding <=> :embedding::vector) <= :threshold
        ORDER BY dc.embedding <=> :embedding::vector
        LIMIT :top_k
    """)

    result = await db.execute(sql, params)
    rows = result.fetchall()

    chunks = []
    for row in rows:
        similarity = max(0.0, 1.0 - float(row.distance))
        chunks.append(
            RetrievedChunk(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                content=row.content,
                page_number=row.page_number,
                section_title=row.section_title,
                document_name=row.document_name,
                similarity_score=round(similarity, 4),
            )
        )

    latency_ms = (time.time() - start) * 1000
    logger.info(
        "Retrieval complete",
        query_len=len(query),
        chunks_found=len(chunks),
        latency_ms=round(latency_ms),
    )
    return chunks, latency_ms
