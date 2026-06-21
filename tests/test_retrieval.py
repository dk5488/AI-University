import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.rag.retrieval import RetrievalService


@pytest.mark.asyncio
async def test_retrieval_service_coordinates_search():
    # Mocks
    embedding_client = AsyncMock()
    embedding_client.embed_text.return_value = [0.1] * 768

    vector_store = AsyncMock()
    vector_store.search.return_value = [
        {
            "content": "Article 32 provides constitutional remedies.",
            "document_id": str(uuid4()),
            "page_start": 45,
            "page_end": 45,
            "chapter": "Fundamental Rights",
            "topic_hint": "Article 32",
        }
    ]

    service = RetrievalService(
        embedding_client=embedding_client,
        vector_store=vector_store,
    )

    # Act
    response = await service.retrieve("Explain Article 32", subject="Polity")

    # Assert
    assert response.query == "Explain Article 32"
    assert len(response.chunks) == 1
    assert response.chunks[0].content == "Article 32 provides constitutional remedies."
    assert response.chunks[0].chapter == "Fundamental Rights"
    
    embedding_client.embed_text.assert_called_once_with("Explain Article 32")
    vector_store.search.assert_called_once_with(
        query_vector=[0.1] * 768,
        limit=5,
        subject="Polity",
        document_id=None,
    )
