from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.learning import Assessment, LearningContext, Progress, RevisionTask, Topic


@dataclass(frozen=True, slots=True)
class ProgressUpdate:
    user_id: UUID
    topic_id: UUID
    completion_percent: int
    confidence_score: int
    last_studied_at: datetime


@dataclass(frozen=True, slots=True)
class SemanticObservation:
    user_id: UUID
    subject_code: str
    topic_slug: str | None
    observation: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.subject_code.strip():
            raise ValueError("subject_code is required")
        if self.topic_slug is not None and not self.topic_slug.strip():
            raise ValueError("topic_slug cannot be blank")
        if not self.observation.strip():
            raise ValueError("observation is required")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")


class StructuredMemoryStore(Protocol):
    async def get_progress(self, user_id: UUID, topic_id: UUID) -> Progress | None:
        ...

    async def upsert_progress(self, update: ProgressUpdate) -> Progress:
        ...

    async def record_assessment(self, assessment: Assessment) -> Assessment:
        ...

    async def list_recent_assessments(
        self,
        user_id: UUID,
        *,
        topic_id: UUID | None = None,
        limit: int = 5,
    ) -> tuple[Assessment, ...]:
        ...

    async def create_revision_tasks(self, tasks: tuple[RevisionTask, ...]) -> tuple[RevisionTask, ...]:
        ...

    async def list_due_revisions(self, user_id: UUID) -> tuple[RevisionTask, ...]:
        ...

    async def list_progress(self, user_id: UUID) -> tuple[Progress, ...]:
        ...

    async def get_topic_by_slug(self, subject_code: str, topic_slug: str) -> Topic | None:
        ...

    async def list_topics(self, subject_code: str) -> tuple[Topic, ...]:
        ...


class SemanticMemoryStore(Protocol):
    async def add_observation(self, observation: SemanticObservation) -> None:
        ...

    async def search_observations(
        self,
        user_id: UUID,
        *,
        subject_code: str,
        topic_slug: str | None = None,
        limit: int = 5,
    ) -> tuple[str, ...]:
        ...


class SessionMemoryStore(Protocol):
    async def get_session(self, user_id: UUID, session_id: str) -> dict[str, object] | None:
        ...

    async def set_session(
        self,
        user_id: UUID,
        session_id: str,
        value: dict[str, object],
        ttl_seconds: int,
    ) -> None:
        ...

    async def clear_session(self, user_id: UUID, session_id: str) -> None:
        ...


class MemoryService:
    def __init__(
        self,
        structured: StructuredMemoryStore,
        semantic: SemanticMemoryStore,
        session: SessionMemoryStore,
    ) -> None:
        self._structured = structured
        self._semantic = semantic
        self._session = session

    async def get_learning_context(
        self,
        *,
        user_id: UUID,
        subject_code: str,
        topic_id: UUID | None = None,
        topic_slug: str | None = None,
    ) -> LearningContext:
        progress = None
        if topic_id is not None:
            progress = await self._structured.get_progress(user_id, topic_id)

        recent_assessments = await self._structured.list_recent_assessments(
            user_id,
            topic_id=topic_id,
        )
        weak_topics = tuple(
            dict.fromkeys(
                weak_topic
                for assessment in recent_assessments
                for weak_topic in assessment.weak_topics
            )
        )
        observations = await self._semantic.search_observations(
            user_id,
            subject_code=subject_code,
            topic_slug=topic_slug,
        )

        return LearningContext(
            user_id=user_id,
            subject_code=subject_code,
            topic_slug=topic_slug,
            progress=progress,
            weak_topics=weak_topics,
            last_studied_at=progress.last_studied_at if progress else None,
            semantic_observations=observations,
        )

    async def record_progress(self, update: ProgressUpdate) -> Progress:
        return await self._structured.upsert_progress(update)

    async def record_assessment(self, assessment: Assessment) -> Assessment:
        return await self._structured.record_assessment(assessment)

    async def add_semantic_observation(self, observation: SemanticObservation) -> None:
        await self._semantic.add_observation(observation)

    async def create_revision_tasks(self, tasks: tuple[RevisionTask, ...]) -> tuple[RevisionTask, ...]:
        return await self._structured.create_revision_tasks(tasks)

    async def list_due_revisions(self, user_id: UUID) -> tuple[RevisionTask, ...]:
        return await self._structured.list_due_revisions(user_id)

    async def list_progress(self, user_id: UUID) -> tuple[Progress, ...]:
        return await self._structured.list_progress(user_id)

    async def get_session(self, user_id: UUID, session_id: str) -> dict[str, object] | None:
        return await self._session.get_session(user_id, session_id)

    async def set_session(
        self,
        user_id: UUID,
        session_id: str,
        value: dict[str, object],
        ttl_seconds: int,
    ) -> None:
        await self._session.set_session(user_id, session_id, value, ttl_seconds)

    async def clear_session(self, user_id: UUID, session_id: str) -> None:
        await self._session.clear_session(user_id, session_id)

    async def get_topic_by_slug(self, subject_code: str, topic_slug: str) -> Topic | None:
        return await self._structured.get_topic_by_slug(subject_code, topic_slug)

    async def list_topics(self, subject_code: str) -> tuple[Topic, ...]:
        return await self._structured.list_topics(subject_code)
