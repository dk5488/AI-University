from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID

from app.domain.documents import Document, DocumentChunk, SourceType
from app.rag.chunking import Chunker
from app.rag.embeddings import EmbeddingClient
from app.rag.extraction import DocumentExtractor
from app.infrastructure.vector.qdrant_client import QdrantVectorStore


class IngestionService:
    def __init__(
        self,
        extractor: DocumentExtractor,
        chunker: Chunker,
        embedding_client: EmbeddingClient,
        vector_store: QdrantVectorStore,
    ) -> None:
        self._extractor = extractor
        self._chunker = chunker
        self._embedding_client = embedding_client
        self._vector_store = vector_store

    async def ingest_document(
        self,
        file_path: Path,
        title: str,
        subject: str | None = None,
        subject_id: UUID | None = None,
    ) -> Document:
        # 1. Calculate version hash for idempotency (simple file hash)
        file_content = file_path.read_bytes()
        version_hash = hashlib.sha256(file_content).hexdigest()

        document = Document(
            title=title,
            source_type=SourceType.PDF if file_path.suffix.lower() == ".pdf" else SourceType.TEXT,
            version_hash=version_hash,
            subject_id=subject_id,
        )

        # 2. Extract
        extracted_chunks = list(self._extractor.extract(file_path))

        # 3. Chunk
        chunks = list(self._chunker.create_chunks(document.id, iter(extracted_chunks)))

        # 3b. Inject subject into each chunk's metadata for filtering
        if subject:
            enriched_chunks = []
            for chunk in chunks:
                enriched_meta = {**chunk.metadata, "subject": subject, "title": title}
                enriched_chunks.append(
                    DocumentChunk(
                        id=chunk.id,
                        document_id=chunk.document_id,
                        content=chunk.content,
                        content_hash=chunk.content_hash,
                        chunk_index=chunk.chunk_index,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                        chapter=chunk.chapter,
                        topic_hint=chunk.topic_hint,
                        metadata=enriched_meta,
                    )
                )
            chunks = enriched_chunks

        # 4. Embed
        texts = [chunk.content for chunk in chunks]
        embeddings = await self._embedding_client.embed_batch(texts)

        # 5. Store in Qdrant
        await self._vector_store.ensure_collection()
        await self._vector_store.upsert_chunks(chunks, embeddings)

        return document
