import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.api.dependencies import get_quiz_service


def test_mcq_lifecycle() -> None:
    # Setup mock QuizService
    mock_quiz_service = AsyncMock()
    assessment_id = uuid4()
    q_id = uuid4()
    
    mock_quiz_service.generate_quiz.return_value = {
        "assessment_id": assessment_id,
        "questions": [
            {
                "id": q_id,
                "stem": "What is Article 32?",
                "options": ["Option A", "Option B", "Option C", "Option D"]
            }
        ]
    }

    mock_quiz_service.submit_quiz.return_value = {
        "score": 1,
        "total": 1,
        "percentage": 100.0,
        "feedback": "Great job!",
        "results": [
            {
                "question_id": q_id,
                "is_correct": True,
                "correct_option": "Option C",
                "user_option": "Option C",
                "explanation": "Article 32 is about constitutional remedies."
            }
        ],
        "weak_topics": []
    }

    # Override dependency
    app.dependency_overrides[get_quiz_service] = lambda: mock_quiz_service

    client = TestClient(app)
    user_id = uuid4()

    # 1. Generate Quiz
    gen_response = client.post(
        f"/api/v1/subjects/polity/topics/fundamental-rights/mcqs?user_id={user_id}&count=1"
    )

    assert gen_response.status_code == 201
    gen_data = gen_response.json()
    assert gen_data["assessment_id"] == str(assessment_id)
    assert len(gen_data["questions"]) == 1

    # 2. Submit Quiz
    sub_response = client.post(
        f"/api/v1/assessments/{assessment_id}/submit",
        json={
            "user_id": str(user_id),
            "answers": [
                {
                    "question_id": str(q_id),
                    "selected_option": "Option C"
                }
            ]
        }
    )

    assert sub_response.status_code == 200
    sub_data = sub_response.json()
    assert sub_data["score"] == 1
    assert sub_data["percentage"] == 100.0

    # Clean up
    app.dependency_overrides.clear()
