import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import UTC, datetime

from app.agents.polity_agent import PolityAgent
from app.memory.contracts import LearningContext
from app.rag.retrieval import RetrievalResponse, RetrievedChunk


@pytest.mark.asyncio
async def test_polity_agent_teach_coordinates_services():
    # Setup mocks
    memory_service = AsyncMock()
    memory_service.get_learning_context.return_value = LearningContext(
        user_id=uuid4(),
        subject_code="polity",
        topic_slug="fundamental-rights",
    )

    retrieval_service = AsyncMock()
    retrieval_service.retrieve.return_value = RetrievalResponse(
        query="Fundamental Rights",
        chunks=[
            RetrievedChunk(
                content="Article 14 ensures equality before law.",
                document_id="doc-1",
                page_start=10,
                page_end=10,
                chapter="Fundamental Rights",
                topic_hint="Article 14",
                metadata={"title": "Indian Polity"},
            )
        ]
    )

    # Mock LLM
    mock_llm_response = MagicMock()
    mock_llm_response.content = "Equality before law is a key pillar of the Indian Constitution."
    
    agent = PolityAgent(memory_service, retrieval_service, api_key="sk-dummy")
    agent._llm = AsyncMock()
    agent._llm.ainvoke.return_value = mock_llm_response

    # Act
    result = await agent.teach(uuid4(), "Fundamental Rights")

    # Assert
    assert result["answer"] == "Equality before law is a key pillar of the Indian Constitution."
    assert result["subject"] == "Polity"
    assert len(result["sources"]) == 1
    assert result["sources"][0]["chapter"] == "Fundamental Rights"
    
    memory_service.get_learning_context.assert_called_once()
    retrieval_service.retrieve.assert_called_once_with(
        query="Fundamental Rights",
        subject="Polity",
        limit=3,
    )
    agent._llm.ainvoke.assert_called_once()
