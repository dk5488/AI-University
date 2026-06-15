from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from app.domain.learning import Assessment, Progress, RevisionTask, Subject, Topic, RevisionStatus
from app.memory.contracts import MemoryService, ProgressUpdate, SemanticObservation


class InMemoryStructuredMemoryStore:
    def __init__(self) -> None:
        self._progress: dict[tuple[UUID, UUID], Progress] = {}
        self._assessments: dict[UUID, list[Assessment]] = defaultdict(list)
        self._revision_tasks: dict[UUID, RevisionTask] = {}
        self._topics: dict[tuple[str, str], Topic] = {}
        self._seed_data()

    def _seed_data(self) -> None:
        polity = Subject(code="polity", name="Indian Polity")
        topics = [
            Topic(subject_id=polity.id, name="Fundamental Rights", slug="fundamental-rights"),
            Topic(subject_id=polity.id, name="DPSP", slug="dpsp"),
            Topic(subject_id=polity.id, name="President", slug="president"),
        ]
        for topic in topics:
            self._topics[("polity", topic.slug)] = topic

    async def get_progress(self, user_id: UUID, topic_id: UUID) -> Progress | None:
        return self._progress.get((user_id, topic_id))

    async def upsert_progress(self, update: ProgressUpdate) -> Progress:
        existing = self._progress.get((update.user_id, update.topic_id))
        progress_kwargs = {
            "user_id": update.user_id,
            "topic_id": update.topic_id,
            "completion_percent": update.completion_percent,
            "confidence_score": update.confidence_score,
            "revision_count": existing.revision_count if existing else 0,
            "last_studied_at": update.last_studied_at,
        }
        if existing is not None:
            progress_kwargs["id"] = existing.id

        progress = Progress(**progress_kwargs)
        self._progress[(update.user_id, update.topic_id)] = progress
        return progress

    async def record_assessment(self, assessment: Assessment) -> Assessment:
        self._assessments[assessment.user_id].append(assessment)
        self._assessments[assessment.user_id].sort(
            key=lambda stored_assessment: stored_assessment.submitted_at,
            reverse=True,
        )
        return assessment

    async def list_recent_assessments(
        self,
        user_id: UUID,
        *,
        topic_id: UUID | None = None,
        limit: int = 5,
    ) -> tuple[Assessment, ...]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        assessments = self._assessments.get(user_id, [])
        if topic_id is not None:
            assessments = [
                assessment for assessment in assessments if assessment.topic_id == topic_id
            ]
        return tuple(assessments[:limit])

    async def create_revision_tasks(self, tasks: tuple[RevisionTask, ...]) -> tuple[RevisionTask, ...]:
        for task in tasks:
            self._revision_tasks[task.id] = task
        return tasks

    async def list_due_revisions(self, user_id: UUID) -> tuple[RevisionTask, ...]:
        now = datetime.now(timezone.utc)
        return tuple(
            task
            for task in self._revision_tasks.values()
            if task.user_id == user_id
            and task.status == RevisionStatus.PENDING
            and task.due_at <= now
        )

    async def get_topic_by_slug(self, subject_code: str, topic_slug: str) -> Topic | None:
        return self._topics.get((subject_code, topic_slug))


class InMemorySemanticMemoryStore:
    def __init__(self) -> None:
        self._observations: dict[UUID, list[SemanticObservation]] = defaultdict(list)

    async def add_observation(self, observation: SemanticObservation) -> None:
        self._observations[observation.user_id].append(observation)
        self._observations[observation.user_id].sort(
            key=lambda stored_observation: stored_observation.created_at,
            reverse=True,
        )

    async def search_observations(
        self,
        user_id: UUID,
        *,
        subject_code: str,
        topic_slug: str | None = None,
        limit: int = 5,
    ) -> tuple[str, ...]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        observations = [
            observation
            for observation in self._observations.get(user_id, [])
            if observation.subject_code == subject_code
            and (topic_slug is None or observation.topic_slug == topic_slug)
        ]
        return tuple(observation.observation for observation in observations[:limit])


class InMemorySessionMemoryStore:
    def __init__(self) -> None:
        self._sessions: dict[tuple[UUID, str], tuple[dict[str, Any], datetime]] = {}

    async def get_session(self, user_id: UUID, session_id: str) -> dict[str, object] | None:
        stored = self._sessions.get((user_id, session_id))
        if stored is None:
            return None

        value, expires_at = stored
        if datetime.now(tz=expires_at.tzinfo) >= expires_at:
            await self.clear_session(user_id, session_id)
            return None

        return dict(value)

    async def set_session(
        self,
        user_id: UUID,
        session_id: str,
        value: dict[str, object],
        ttl_seconds: int,
    ) -> None:
        if not session_id.strip():
            raise ValueError("session_id is required")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        expires_at = datetime.now().astimezone() + timedelta(seconds=ttl_seconds)
        self._sessions[(user_id, session_id)] = (dict(value), expires_at)

    async def clear_session(self, user_id: UUID, session_id: str) -> None:
        self._sessions.pop((user_id, session_id), None)


def create_in_memory_memory_service() -> MemoryService:
    return MemoryService(
        structured=InMemoryStructuredMemoryStore(),
        semantic=InMemorySemanticMemoryStore(),
        session=InMemorySessionMemoryStore(),
    )
