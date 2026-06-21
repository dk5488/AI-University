import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.rag.ingestion import IngestionService
from app.rag.extraction import ExtractedChunk
from app.domain.documents import DocumentChunk


@pytest.mark.asyncio
async def test_ingestion_service_coordinates_workflow(tmp_path):
    # Setup mock file
    file_path = tmp_path / "test.pdf"
    file_path.write_bytes(b"dummy pdf content")

    # Mocks
    extractor = MagicMock()
    extractor.extract.return_value = iter([
        ExtractedChunk(content="Page 1 content", page_number=1, metadata={}),
        ExtractedChunk(content="Page 2 content", page_number=2, metadata={}),
    ])

    chunker = MagicMock()
    # Simple mock chunking: 1 chunk per page
    def side_effect(doc_id, extracted):
        for i, ex in enumerate(extracted):
            yield DocumentChunk(
                document_id=doc_id,
                content=ex.content,
                content_hash=str(i),
                chunk_index=i,
                page_start=ex.page_number,
                page_end=ex.page_number,
            )
    chunker.create_chunks.side_effect = side_effect

    embedding_client = AsyncMock()
    embedding_client.embed_batch.return_value = [[0.1] * 768, [0.2] * 768]

    vector_store = AsyncMock()

    service = IngestionService(
        extractor=extractor,
        chunker=chunker,
        embedding_client=embedding_client,
        vector_store=vector_store,
    )

    # Act
    document = await service.ingest_document(file_path, "Test Document")

    # Assert
    assert document.title == "Test Document"
    assert extractor.extract.called
    assert chunker.create_chunks.called
    assert embedding_client.embed_batch.called
    assert vector_store.ensure_collection.called
    assert vector_store.upsert_chunks.called
