from __future__ import annotations

from typing import Any
from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from app.domain.documents import DocumentChunk


class QdrantVectorStore:
    def __init__(
        self,
        url: str,
        collection_name: str = "book_chunks",
        vector_size: int = 1536,  # Default for text-embedding-3-small
    ) -> None:
        self._client = AsyncQdrantClient(url=url)
        self._collection_name = collection_name
        self._vector_size = vector_size

    async def ensure_collection(self) -> None:
        collections = await self._client.get_collections()
        exists = any(c.name == self._collection_name for c in collections.collections)
        if not exists:
            await self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=models.VectorParams(
                    size=self._vector_size,
                    distance=models.Distance.COSINE,
                ),
            )

    async def upsert_chunks(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> None:
        points = []
        for chunk, embedding in zip(chunks, embeddings):
            points.append(
                models.PointStruct(
                    id=str(chunk.id),
                    vector=embedding,
                    payload={
                        "document_id": str(chunk.document_id),
                        "content": chunk.content,
                        "content_hash": chunk.content_hash,
                        "chunk_index": chunk.chunk_index,
                        "page_start": chunk.page_start,
                        "page_end": chunk.page_end,
                        "chapter": chunk.chapter,
                        "topic_hint": chunk.topic_hint,
                        **chunk.metadata,
                    },
                )
            )
        
        await self._client.upsert(
            collection_name=self._collection_name,
            points=points,
        )
