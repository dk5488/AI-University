from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies import get_curriculum_service
from app.application.curriculum_service import CurriculumService


router = APIRouter(tags=["curriculum"])


class CurriculumTreeResponse(BaseModel):
    subject_code: str
    tree: list[dict[str, Any]]
    total_nodes: int


class CurriculumProgressResponse(BaseModel):
    subject_code: str
    total_nodes: int
    total_leaf_nodes: int
    completed_leaf_nodes: int
    in_progress_count: int
    completion_percent: int
    current_position: dict[str, Any] | None


@router.get("/subjects/{subject_code}/curriculum", response_model=CurriculumTreeResponse)
async def get_curriculum(
    subject_code: str,
    curriculum_service: CurriculumService = Depends(get_curriculum_service),
) -> dict[str, Any]:
    """Get the full curriculum tree for a subject."""
    tree = await curriculum_service.get_curriculum_tree(subject_code)
    nodes = await curriculum_service.ensure_curriculum(subject_code)
    return {
        "subject_code": subject_code,
        "tree": tree,
        "total_nodes": len(nodes),
    }


@router.get(
    "/users/{user_id}/subjects/{subject_code}/progress",
    response_model=CurriculumProgressResponse,
)
async def get_curriculum_progress(
    user_id: UUID,
    subject_code: str,
    curriculum_service: CurriculumService = Depends(get_curriculum_service),
) -> dict[str, Any]:
    """Get a user's progress through the curriculum."""
    return await curriculum_service.get_user_progress_summary(user_id, subject_code)


@router.post("/subjects/{subject_code}/curriculum/generate")
async def generate_curriculum(
    subject_code: str,
    curriculum_service: CurriculumService = Depends(get_curriculum_service),
) -> dict[str, Any]:
    """Trigger curriculum generation (or reload from cache)."""
    nodes = await curriculum_service.ensure_curriculum(subject_code)
    return {
        "subject_code": subject_code,
        "total_nodes": len(nodes),
        "status": "ready",
    }
