from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.sessions import StudySession
from app.memory.contracts import MemoryService


DEFAULT_SESSION_TTL_SECONDS = 4 * 60 * 60


@dataclass(frozen=True, slots=True)
class StartStudySessionCommand:
    user_id: UUID
    subject_code: str
    started_at: datetime
    topic_slug: str | None = None
    ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS

    def __post_init__(self) -> None:
        if not self.subject_code.strip():
            raise ValueError("subject_code is required")
        if self.topic_slug is not None and not self.topic_slug.strip():
            raise ValueError("topic_slug cannot be blank")
        if self.started_at.tzinfo is None:
            raise ValueError("started_at must be timezone-aware")
        if self.ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")


class StudySessionService:
    def __init__(self, memory_service: MemoryService) -> None:
        self._memory_service = memory_service

    async def start_session(self, command: StartStudySessionCommand) -> StudySession:
        session = StudySession(
            session_id=str(uuid4()),
            user_id=command.user_id,
            subject_code=command.subject_code,
            topic_slug=command.topic_slug,
            started_at=command.started_at,
            last_activity_at=command.started_at,
        )
        await self._memory_service.set_session(
            command.user_id,
            session.session_id,
            session.to_memory_dict(),
            ttl_seconds=command.ttl_seconds,
        )
        return session

    async def get_session(self, user_id: UUID, session_id: str) -> StudySession | None:
        stored = await self._memory_service.get_session(user_id, session_id)
        if stored is None:
            return None
        return StudySession.from_memory_dict(stored)

    async def end_session(self, user_id: UUID, session_id: str) -> StudySession | None:
        session = await self.get_session(user_id, session_id)
        await self._memory_service.clear_session(user_id, session_id)
        return session
