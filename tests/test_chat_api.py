import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.api.dependencies import get_chat_service


def test_chat_endpoint_routing() -> None:
    # Setup mock ChatService
    mock_chat_service = AsyncMock()
    mock_chat_service.chat.return_value = {
        "answer": "Fundamental Rights are basic rights guaranteed by the Constitution.",
        "subject": "polity",
        "topic": "Fundamental Rights",
        "sources": [
            {
                "title": "Indian Polity",
                "chapter": "Fundamental Rights",
                "page_start": 123
            }
        ],
        "next_actions": ["Generate MCQs"]
    }

    # Override dependency
    app.dependency_overrides[get_chat_service] = lambda: mock_chat_service

    client = TestClient(app)
    user_id = uuid4()

    response = client.post(
        "/api/v1/chat",
        json={
            "user_id": str(user_id),
            "message": "Teach me about Fundamental Rights"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "Fundamental Rights" in data["answer"]
    assert data["subject"] == "polity"
    assert len(data["sources"]) == 1
    assert data["sources"][0]["title"] == "Indian Polity"

    # Clean up
    app.dependency_overrides.clear()
