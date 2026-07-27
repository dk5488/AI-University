"""
RAG Pipeline HTTP Client — calls the RAG Pipeline's FastAPI ``/search``
endpoint to retrieve relevant document chunks from the knowledge base.

The RAG Pipeline handles embedding (FastEmbed / BGE-small) and vector
search (Qdrant Cloud / ``rag_notes`` collection) internally.  This
client is a thin async wrapper that sends the query and returns the
results.
"""

from __future__ import annotations

import logging
import time

import httpx

logger = logging.getLogger(__name__)


class RagPipelineClient:
    """
    Async HTTP client for the RAG Pipeline search API.

    Usage::

        client = RagPipelineClient("http://localhost:8001")
        results = await client.search("What are Fundamental Rights?")
        # results is a formatted string with citations
    """

    def __init__(self, base_url: str = "http://localhost:8001") -> None:
        self._base_url = base_url.rstrip("/")
        logger.info("rag_pipeline_client_initialized base_url=%s", self._base_url)

    async def search(self, query: str) -> str:
        """
        Search the RAG Pipeline's knowledge base.

        Calls ``POST /search`` on the RAG Pipeline API.  Returns the
        formatted results string with citations (filename, page number,
        relevance score) or an empty string on failure.

        The RAG Pipeline handles:
        - Embedding the query with FastEmbed (BAAI/bge-small-en-v1.5)
        - Searching the ``rag_notes`` Qdrant Cloud collection
        - Formatting results with source citations
        """
        start_time = time.perf_counter()
        logger.info(
            "rag_pipeline_search_start query_length=%s base_url=%s",
            len(query),
            self._base_url,
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._base_url}/search",
                    json={"query": query},
                )
                response.raise_for_status()
                data = response.json()
                results = data.get("results", "")

            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "rag_pipeline_search_complete result_length=%s duration_ms=%.2f",
                len(results),
                duration_ms,
            )
            return results

        except httpx.ConnectError:
            logger.warning(
                "rag_pipeline_search_failed reason=connection_refused base_url=%s "
                "(is the RAG Pipeline API running?)",
                self._base_url,
            )
            return ""

        except httpx.TimeoutException:
            logger.warning(
                "rag_pipeline_search_failed reason=timeout base_url=%s",
                self._base_url,
            )
            return ""

        except Exception:
            logger.exception(
                "rag_pipeline_search_failed query_length=%s base_url=%s",
                len(query),
                self._base_url,
            )
            # Return empty so the chat flow continues without RAG context
            return ""

    async def is_available(self) -> bool:
        """Check if the RAG Pipeline API is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/docs")
                return response.status_code == 200
        except Exception:
            return False
