"""
Embedding service with provider abstraction.
Supports Google Gemini embeddings with a fake provider for unit tests.
"""
import asyncio
import time
from abc import ABC, abstractmethod
from typing import List, Optional

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class EmbeddingProvider(ABC):
    """Abstract embedding provider interface."""

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Embed a single text string."""
        ...

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts efficiently."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return embedding vector dimension."""
        ...


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Google Gemini embedding provider."""

    def __init__(self):
        import google.generativeai as genai
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self._genai = genai
        self._model = settings.EMBEDDING_MODEL

    @property
    def dimension(self) -> int:
        return settings.EMBEDDING_DIMENSION

    async def embed_text(self, text: str) -> List[float]:
        return (await self.embed_batch([text]))[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed texts in batches with retry logic."""
        from tenacity import retry, stop_after_attempt, wait_exponential

        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
        def _embed(batch: List[str]) -> List[List[float]]:
            result = self._genai.embed_content(
                model=self._model,
                content=batch,
                task_type="retrieval_document",
            )
            return result["embedding"] if len(batch) == 1 else [r for r in result["embedding"]]

        # Process in batches of 100
        all_embeddings = []
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                embeddings = await asyncio.to_thread(_embed, batch)
                if isinstance(embeddings[0], float):
                    # Single text returned as flat list
                    embeddings = [embeddings]
                all_embeddings.extend(embeddings)
                logger.debug("Embedded batch", batch_size=len(batch), offset=i)
            except Exception as e:
                logger.error("Embedding failed", error=str(e), batch_offset=i)
                raise
        return all_embeddings


class FakeEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic fake embedding provider for unit tests.
    Produces consistent vectors based on text hash without API calls.
    """

    def __init__(self, dim: int = 768):
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed_text(self, text: str) -> List[float]:
        import hashlib
        import struct
        h = hashlib.sha256(text.encode()).digest()
        needed_bytes = self._dim * 4
        extended = (h * (needed_bytes // len(h) + 1))[:needed_bytes]
        floats = list(struct.unpack(f"{self._dim}f", extended))
        # Normalize
        mag = sum(x**2 for x in floats) ** 0.5 or 1.0
        return [x / mag for x in floats]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [await self.embed_text(t) for t in texts]


def get_embedding_provider(provider: Optional[str] = None) -> EmbeddingProvider:
    """Factory: return the configured embedding provider."""
    if provider == "fake" or settings.APP_ENV == "test":
        return FakeEmbeddingProvider(dim=settings.EMBEDDING_DIMENSION)
    if not settings.GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY not set — falling back to FakeEmbeddingProvider")
        return FakeEmbeddingProvider(dim=settings.EMBEDDING_DIMENSION)
    return GeminiEmbeddingProvider()


# Singleton — initialized at startup
_provider: Optional[EmbeddingProvider] = None


def embedding_service() -> EmbeddingProvider:
    global _provider
    if _provider is None:
        _provider = get_embedding_provider()
    return _provider
