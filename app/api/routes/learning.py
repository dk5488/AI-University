from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies import get_learning_service
from app.application.learning_service import LearningService


router = APIRouter(prefix="/users/{user_id}", tags=["learning"])


class ProgressItem(BaseModel):
    topic_name: str
    topic_slug: str
    completion_percent: int
    confidence_score: int
    last_studied_at: datetime


class RevisionItem(BaseModel):
    task_id: UUID
    topic_name: str
    topic_slug: str
    due_at: datetime
    reason: str


class SubjectSummary(BaseModel):
    code: str
    name: str
    topics_count: int


class UserDashboardResponse(BaseModel):
    user_id: UUID
    progress: list[ProgressItem]
    due_revisions: list[RevisionItem]
    available_subjects: list[SubjectSummary]


@router.get("/dashboard", response_model=UserDashboardResponse)
async def get_dashboard(
    user_id: UUID,
    learning_service: LearningService = Depends(get_learning_service),
) -> dict[str, Any]:
    return await learning_service.get_user_dashboard(user_id)
