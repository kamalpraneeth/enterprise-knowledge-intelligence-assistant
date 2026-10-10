"""
LLM provider abstraction with Google Gemini implementation.
Handles generation, timeouts, retries, and structured output.
"""
import asyncio
import time
from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    @abstractmethod
    async def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        ...

    @abstractmethod
    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        ...


class GeminiLLMProvider(LLMProvider):
    """Google Gemini LLM provider."""

    def __init__(self):
        import google.generativeai as genai
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self._model = genai.GenerativeModel(
            model_name=settings.LLM_MODEL,
            generation_config={
                "temperature": settings.LLM_TEMPERATURE,
                "max_output_tokens": settings.LLM_MAX_TOKENS,
            },
        )
        self._genai = genai

    async def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        from tenacity import retry, stop_after_attempt, wait_exponential

        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=30))
        def _call():
            response = self._model.generate_content(prompt)
            return response.text

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_call),
                timeout=60.0,
            )
        except asyncio.TimeoutError:
            logger.error("LLM generation timed out")
            raise RuntimeError("LLM generation timed out. Please try again.")
        except Exception as e:
            logger.error("LLM generation failed", error=str(e))
            raise

    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        def _stream():
            return self._model.generate_content(prompt, stream=True)

        stream = await asyncio.to_thread(_stream)
        for chunk in stream:
            if chunk.text:
                yield chunk.text


class FakeLLMProvider(LLMProvider):
    """Deterministic fake LLM for unit tests."""

    async def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        # Return a structured deterministic response based on prompt content
        if "cannot determine" in prompt.lower() or "no sources" in prompt.lower():
            return "I cannot determine the answer from the available documents."
        return (
            "Based on the available documents, the policy states that standard procedures apply. "
            "**Sources:** [Source 1] Test Document (Page 1)"
        )

    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        response = await self.generate(prompt)
        for word in response.split():
            yield word + " "


def get_llm_provider() -> LLMProvider:
    """Factory for the configured LLM provider."""
    if settings.APP_ENV == "test":
        return FakeLLMProvider()
    if not settings.GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY not set — using FakeLLMProvider")
        return FakeLLMProvider()
    return GeminiLLMProvider()


_llm_provider: Optional[LLMProvider] = None


def llm_service() -> LLMProvider:
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = get_llm_provider()
    return _llm_provider
