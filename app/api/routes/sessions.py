from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies import get_memory_service
from app.application.session_service import (
    DEFAULT_SESSION_TTL_SECONDS,
    StartStudySessionCommand,
    StudySessionService,
)
from app.domain.sessions import StudySession
from app.memory.contracts import MemoryService


router = APIRouter(prefix="/users/{user_id}/sessions", tags=["sessions"])


class StartSessionRequest(BaseModel):
    subject_code: str = Field(min_length=1)
    topic_slug: str | None = Field(default=None, min_length=1)
    ttl_seconds: int = Field(default=DEFAULT_SESSION_TTL_SECONDS, gt=0)


class StudySessionResponse(BaseModel):
    session_id: str
    user_id: UUID
    subject_code: str
    topic_slug: str | None
    started_at: datetime
    last_activity_at: datetime
    time_spent_seconds: int
    current_mcq_score: int | None

    @classmethod
    def from_domain(cls, session: StudySession) -> "StudySessionResponse":
        return cls(
            session_id=session.session_id,
            user_id=session.user_id,
            subject_code=session.subject_code,
            topic_slug=session.topic_slug,
            started_at=session.started_at,
            last_activity_at=session.last_activity_at,
            time_spent_seconds=session.time_spent_seconds,
            current_mcq_score=session.current_mcq_score,
        )


@router.post("", response_model=StudySessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    user_id: UUID,
    request: StartSessionRequest,
    memory_service: MemoryService = Depends(get_memory_service),
) -> StudySessionResponse:
    service = StudySessionService(memory_service)
    session = await service.start_session(
        StartStudySessionCommand(
            user_id=user_id,
            subject_code=request.subject_code,
            topic_slug=request.topic_slug,
            started_at=datetime.now().astimezone(),
            ttl_seconds=request.ttl_seconds,
        )
    )
    return StudySessionResponse.from_domain(session)


@router.get("/{session_id}", response_model=StudySessionResponse)
async def get_session(
    user_id: UUID,
    session_id: str,
    memory_service: MemoryService = Depends(get_memory_service),
) -> StudySessionResponse:
    service = StudySessionService(memory_service)
    session = await service.get_session(user_id, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return StudySessionResponse.from_domain(session)


@router.delete("/{session_id}", response_model=StudySessionResponse)
async def end_session(
    user_id: UUID,
    session_id: str,
    memory_service: MemoryService = Depends(get_memory_service),
) -> StudySessionResponse:
    service = StudySessionService(memory_service)
    session = await service.end_session(user_id, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return StudySessionResponse.from_domain(session)
