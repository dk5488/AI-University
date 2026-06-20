from __future__ import annotations

import asyncio
import logging
import time
from typing import Protocol

from langchain_google_genai import GoogleGenerativeAIEmbeddings

logger = logging.getLogger(__name__)


class EmbeddingClient(Protocol):
    async def embed_text(self, text: str) -> list[float]:
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...


class GeminiEmbeddingClient:
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-embedding-2-preview",
        output_dimensionality: int = 768,
    ) -> None:
        kwargs: dict[str, object] = {
            "model": model,
            "output_dimensionality": output_dimensionality,
        }
        if api_key:
            kwargs["api_key"] = api_key

        try:
            self._client = GoogleGenerativeAIEmbeddings(**kwargs)
        except TypeError:
            if api_key:
                kwargs.pop("api_key", None)
                kwargs["google_api_key"] = api_key
            self._client = GoogleGenerativeAIEmbeddings(**kwargs)

        self._model = model
        self._output_dimensionality = output_dimensionality
        logger.info(
            "gemini_embedding_client_initialized model=%s output_dimensionality=%s api_key_configured=%s",
            model,
            output_dimensionality,
            bool(api_key),
        )

    async def embed_text(self, text: str) -> list[float]:
        start_time = time.perf_counter()
        logger.info("gemini_embedding_text_start model=%s input_length=%s", self._model, len(text))
        try:
            embedding = await asyncio.to_thread(self._client.embed_query, text)
        except Exception:
            logger.exception("gemini_embedding_text_failed model=%s input_length=%s", self._model, len(text))
            raise
        logger.info(
            "gemini_embedding_text_complete model=%s vector_dimensions=%s duration_ms=%.2f",
            self._model,
            len(embedding),
            (time.perf_counter() - start_time) * 1000,
        )
        return embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            logger.info("gemini_embedding_batch_skipped reason=empty_input")
            return []
        start_time = time.perf_counter()
        logger.info(
            "gemini_embedding_batch_start model=%s input_count=%s total_chars=%s",
            self._model,
            len(texts),
            sum(len(text) for text in texts),
        )
        try:
            embeddings = await asyncio.to_thread(self._client.embed_documents, texts)
        except Exception:
            logger.exception("gemini_embedding_batch_failed model=%s input_count=%s", self._model, len(texts))
            raise
        dimensions = len(embeddings[0]) if embeddings else 0
        logger.info(
            "gemini_embedding_batch_complete model=%s output_count=%s vector_dimensions=%s duration_ms=%.2f",
            self._model,
            len(embeddings),
            dimensions,
            (time.perf_counter() - start_time) * 1000,
        )
        return embeddings
