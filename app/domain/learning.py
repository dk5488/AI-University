from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4


class AssessmentType(StrEnum):
    MCQ = "mcq"
    REVISION = "revision"


class RevisionStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class User:
    display_name: str
    timezone: str = "Asia/Calcutta"
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.display_name.strip():
            raise ValueError("display_name is required")
        if not self.timezone.strip():
            raise ValueError("timezone is required")


@dataclass(frozen=True, slots=True)
class Subject:
    code: str
    name: str
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("subject code is required")
        if not self.name.strip():
            raise ValueError("subject name is required")


@dataclass(frozen=True, slots=True)
class Topic:
    subject_id: UUID
    name: str
    slug: str
    order: int = 0
    parent_topic_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("topic name is required")
        if not self.slug.strip():
            raise ValueError("topic slug is required")
        if self.order < 0:
            raise ValueError("order cannot be negative")


@dataclass(frozen=True, slots=True)
class Progress:
    user_id: UUID
    topic_id: UUID
    completion_percent: int = 0
    confidence_score: int = 1
    revision_count: int = 0
    last_studied_at: datetime | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        _ensure_range(self.completion_percent, "completion_percent", minimum=0, maximum=100)
        _ensure_range(self.confidence_score, "confidence_score", minimum=1, maximum=10)
        if self.revision_count < 0:
            raise ValueError("revision_count cannot be negative")


@dataclass(frozen=True, slots=True)
class Assessment:
    user_id: UUID
    topic_id: UUID
    assessment_type: AssessmentType
    score: int
    total: int
    submitted_at: datetime
    weak_topics: tuple[str, ...] = ()
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.total <= 0:
            raise ValueError("assessment total must be positive")
        _ensure_range(self.score, "score", minimum=0, maximum=self.total)
        if self.submitted_at.tzinfo is None:
            raise ValueError("submitted_at must be timezone-aware")
        _ensure_non_empty_strings(self.weak_topics, "weak_topics")

    @property
    def percentage(self) -> float:
        return self.score / self.total * 100


@dataclass(frozen=True, slots=True)
class RevisionTask:
    user_id: UUID
    topic_id: UUID
    due_at: datetime
    reason: str
    status: RevisionStatus = RevisionStatus.PENDING
    source_assessment_id: UUID | None = None
    completed_at: datetime | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.due_at.tzinfo is None:
            raise ValueError("due_at must be timezone-aware")
        if not self.reason.strip():
            raise ValueError("revision reason is required")
        if self.completed_at is not None and self.completed_at.tzinfo is None:
            raise ValueError("completed_at must be timezone-aware")
        if self.status != RevisionStatus.COMPLETED and self.completed_at is not None:
            raise ValueError("completed_at is only valid for completed revision tasks")

    def complete(self, completed_at: datetime) -> RevisionTask:
        return RevisionTask(
            user_id=self.user_id,
            topic_id=self.topic_id,
            due_at=self.due_at,
            reason=self.reason,
            status=RevisionStatus.COMPLETED,
            source_assessment_id=self.source_assessment_id,
            completed_at=completed_at,
            id=self.id,
        )


@dataclass(frozen=True, slots=True)
class LearningContext:
    user_id: UUID
    subject_code: str
    topic_slug: str | None
    progress: Progress | None = None
    weak_topics: tuple[str, ...] = ()
    last_studied_at: datetime | None = None
    semantic_observations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.subject_code.strip():
            raise ValueError("subject_code is required")
        _ensure_optional_non_empty(self.topic_slug, "topic_slug")
        _ensure_non_empty_strings(self.weak_topics, "weak_topics")
        _ensure_non_empty_strings(self.semantic_observations, "semantic_observations")


def _ensure_range(value: int, name: str, *, minimum: int, maximum: int) -> None:
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")


def _ensure_non_empty_strings(values: tuple[str, ...], name: str) -> None:
    if any(not value.strip() for value in values):
        raise ValueError(f"{name} cannot contain blank values")


def _ensure_optional_non_empty(value: str | None, name: str) -> None:
    if value is not None and not value.strip():
        raise ValueError(f"{name} cannot be blank")
