from __future__ import annotations

import asyncio
import logging
import time
from typing import Protocol

from langchain_google_genai import GoogleGenerativeAIEmbeddings

logger = logging.getLogger(__name__)

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
            kwargs["google_api_key"] = api_key

        try:
            self._client = GoogleGenerativeAIEmbeddings(**kwargs)
        except TypeError:
            # Fallback for older versions that use 'api_key' instead
            if api_key:
                kwargs.pop("google_api_key", None)
                kwargs["api_key"] = api_key
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

    async def embed_batch(self, texts: list[str], batch_size: int = 20) -> list[list[float]]:
        if not texts:
            logger.info("gemini_embedding_batch_skipped reason=empty_input")
            return []
        start_time = time.perf_counter()
        logger.info(
            "gemini_embedding_batch_start model=%s input_count=%s total_chars=%s batch_size=%s",
            self._model,
            len(texts),
            sum(len(text) for text in texts),
            batch_size,
        )

        all_embeddings: list[list[float]] = []
        total_batches = (len(texts) + batch_size - 1) // batch_size

        for batch_idx in range(0, len(texts), batch_size):
            batch = texts[batch_idx : batch_idx + batch_size]
            batch_num = batch_idx // batch_size + 1
            logger.info(
                "gemini_embedding_batch_chunk model=%s batch=%s/%s chunk_count=%s",
                self._model, batch_num, total_batches, len(batch),
            )

            # Retry with exponential backoff for rate limits and timeouts
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    batch_embeddings = await asyncio.to_thread(
                        self._client.embed_documents, batch
                    )
                    # Truncate to output_dimensionality — langchain's embed_documents
                    # ignores output_dimensionality unlike embed_query
                    batch_embeddings = [
                        emb[:self._output_dimensionality] for emb in batch_embeddings
                    ]
                    all_embeddings.extend(batch_embeddings)
                    break
                except Exception as e:
                    error_str = str(e)
                    is_retryable = "429" in error_str or "504" in error_str or "Deadline" in error_str
                    if is_retryable and attempt < max_retries - 1:
                        wait_time = min(2 ** attempt * 5, 60)  # 5s, 10s, 20s, 40s, 60s
                        logger.warning(
                            "gemini_embedding_batch_retry model=%s batch=%s/%s attempt=%s wait_seconds=%s error=%s",
                            self._model, batch_num, total_batches, attempt + 1, wait_time, error_str[:100],
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.exception(
                            "gemini_embedding_batch_failed model=%s batch=%s/%s attempts=%s",
                            self._model, batch_num, total_batches, attempt + 1,
                        )
                        raise

            # Pause between batches to respect rate limits (100 req/min free tier)
            if batch_idx + batch_size < len(texts):
                await asyncio.sleep(2)

        dimensions = len(all_embeddings[0]) if all_embeddings else 0
        logger.info(
            "gemini_embedding_batch_complete model=%s output_count=%s vector_dimensions=%s duration_ms=%.2f",
            self._model,
            len(all_embeddings),
            dimensions,
            (time.perf_counter() - start_time) * 1000,
        )
        return all_embeddings

