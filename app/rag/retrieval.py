from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from app.rag.embeddings import EmbeddingClient
from app.infrastructure.vector.qdrant_client import QdrantVectorStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    content: str
    document_id: str
    page_start: int | None
    page_end: int | None
    chapter: str | None
    topic_hint: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RetrievalResponse:
    query: str
    chunks: list[RetrievedChunk]


class RetrievalService:
    def __init__(
        self,
        embedding_client: EmbeddingClient,
        vector_store: QdrantVectorStore,
        reranker: Any = None,
    ) -> None:
        self._embedding_client = embedding_client
        self._vector_store = vector_store
        self._reranker = reranker

    async def retrieve(
        self,
        query: str,
        *,
        limit: int = 5,
        subject: str | None = None,
        document_id: str | None = None,
    ) -> RetrievalResponse:
        start_time = time.perf_counter()
        logger.info(
            "retrieval_start subject=%s document_id=%s limit=%s query_length=%s",
            subject,
            document_id,
            limit,
            len(query),
        )

        # 1. Embed query
        try:
            query_vector = await self._embedding_client.embed_text(query)
        except Exception:
            logger.exception("retrieval_embedding_failed subject=%s document_id=%s query_length=%s", subject, document_id, len(query))
            raise
        logger.info("retrieval_embedding_complete vector_dimensions=%s", len(query_vector))

        # 2. Search vector store
        try:
            payloads = await self._vector_store.search(
                query_vector=query_vector,
                limit=limit,
                subject=subject,
                document_id=document_id,
            )
        except Exception:
            logger.exception("retrieval_vector_search_failed subject=%s document_id=%s limit=%s", subject, document_id, limit)
            raise
        logger.info("retrieval_vector_search_complete payload_count=%s", len(payloads))

        # 3. Map to domain model
        chunks = [
            RetrievedChunk(
                content=str(p["content"]),
                document_id=str(p["document_id"]),
                page_start=p.get("page_start"),
                page_end=p.get("page_end"),
                chapter=p.get("chapter"),
                topic_hint=p.get("topic_hint"),
                metadata={k: v for k, v in p.items() if k not in {
                    "content", "document_id", "page_start", "page_end", "chapter", "topic_hint"
                }},
            )
            for p in payloads
        ]

        # 4. Optional reranking hook
        if self._reranker:
            logger.info("retrieval_rerank_start chunk_count=%s", len(chunks))
            chunks = await self._reranker.rerank(query, chunks)
            logger.info("retrieval_rerank_complete chunk_count=%s", len(chunks))

        logger.info(
            "retrieval_complete subject=%s document_id=%s chunk_count=%s duration_ms=%.2f",
            subject,
            document_id,
            len(chunks),
            (time.perf_counter() - start_time) * 1000,
        )
        return RetrievalResponse(query=query, chunks=chunks)
