from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies import get_quiz_service
from app.application.quiz_service import QuizService


router = APIRouter(tags=["mcqs"])


class MCQResponse(BaseModel):
    id: UUID
    stem: str
    options: list[str]


class QuizResponse(BaseModel):
    assessment_id: UUID
    questions: list[MCQResponse]


class UserAnswerRequest(BaseModel):
    question_id: UUID
    selected_option: str


class QuizSubmissionRequest(BaseModel):
    user_id: UUID
    answers: list[UserAnswerRequest]


class MCQResultResponse(BaseModel):
    question_id: UUID
    is_correct: bool
    correct_option: str
    user_option: str | None
    explanation: str


class QuizSubmissionResponse(BaseModel):
    score: int
    total: int
    percentage: float
    feedback: str
    results: list[MCQResultResponse]
    weak_topics: list[str]


@router.post(
    "/subjects/{subject_code}/topics/{topic_slug}/mcqs",
    response_model=QuizResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_quiz(
    subject_code: str,
    topic_slug: str,
    user_id: UUID,
    count: int = 5,
    quiz_service: QuizService = Depends(get_quiz_service),
) -> dict[str, Any]:
    try:
        return await quiz_service.generate_quiz(
            user_id=user_id,
            subject_code=subject_code,
            topic_slug=topic_slug,
            count=count,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/assessments/{assessment_id}/submit",
    response_model=QuizSubmissionResponse,
)
async def submit_quiz(
    assessment_id: UUID,
    request: QuizSubmissionRequest,
    quiz_service: QuizService = Depends(get_quiz_service),
) -> dict[str, Any]:
    try:
        return await quiz_service.submit_quiz(
            user_id=request.user_id,
            assessment_id=assessment_id,
            answers=[a.model_dump() for a in request.answers],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
