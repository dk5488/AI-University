from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_revision_service
from app.application.revision_service import RevisionService


router = APIRouter(prefix="/users/{user_id}/revisions", tags=["revisions"])


class RevisionItemResponse(BaseModel):
    revision_task_id: UUID
    topic_id: UUID
    due_at: datetime
    reason: str
    status: str


class DueRevisionsResponse(BaseModel):
    items: list[RevisionItemResponse]


@router.get("/due", response_model=DueRevisionsResponse)
async def get_due_revisions(
    user_id: UUID,
    revision_service: RevisionService = Depends(get_revision_service),
) -> dict[str, Any]:
    items = await revision_service.get_due_revisions(user_id)
    return {"items": list(items)}
