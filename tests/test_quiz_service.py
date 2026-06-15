import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from app.application.quiz_service import QuizService
from app.agents.polity_agent import QuizSchema, MCQSchema


@pytest.mark.asyncio
async def test_quiz_service_generate_and_submit():
    memory_service = AsyncMock()
    polity_agent = AsyncMock()
    
    # Mock topic resolution
    topic_id = uuid4()
    topic_mock = MagicMock()
    topic_mock.id = topic_id
    topic_mock.name = "Fundamental Rights"
    topic_mock.slug = "fundamental-rights"
    memory_service.get_topic_by_slug.return_value = topic_mock
    
    # Mock MCQ generation
    polity_agent.generate_mcqs.return_value = QuizSchema(
        questions=[
            MCQSchema(
                stem="What is Article 32?",
                options=["A", "B", "C", "D"],
                correct_option="C",
                explanation="Right to constitutional remedies."
            )
        ]
    )
    
    service = QuizService(memory_service, polity_agent)
    user_id = uuid4()
    
    # 1. Generate
    quiz_data = await service.generate_quiz(user_id, "polity", "fundamental-rights")
    
    assert "assessment_id" in quiz_data
    assert len(quiz_data["questions"]) == 1
    memory_service.set_session.assert_called_once()
    
    # 2. Submit
    assessment_id = quiz_data["assessment_id"]
    q_id = quiz_data["questions"][0]["id"]
    
    # Mock session retrieval
    memory_service.get_session.return_value = {
        "topic_id": str(topic_id),
        "topic_name": "Fundamental Rights",
        "questions": [
            {
                "id": str(q_id),
                "stem": "What is Article 32?",
                "options": ["A", "B", "C", "D"],
                "correct_option": "C",
                "explanation": "Right to constitutional remedies."
            }
        ]
    }
    
    # Mock feedback
    polity_agent.evaluate_mcq_submission.return_value = "Keep it up!"
    
    result = await service.submit_quiz(
        user_id, 
        assessment_id, 
        [{"question_id": str(q_id), "selected_option": "C"}]
    )
    
    assert result["score"] == 1
    assert result["total"] == 1
    assert result["feedback"] == "Keep it up!"
    memory_service.record_assessment.assert_called_once()
    memory_service.clear_session.assert_called_once()
