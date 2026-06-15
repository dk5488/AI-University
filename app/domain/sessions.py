from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StudySession:
    session_id: str
    user_id: UUID
    subject_code: str
    started_at: datetime
    last_activity_at: datetime
    topic_slug: str | None = None
    time_spent_seconds: int = 0
    current_mcq_score: int | None = None

    def __post_init__(self) -> None:
        if not self.session_id.strip():
            raise ValueError("session_id is required")
        if not self.subject_code.strip():
            raise ValueError("subject_code is required")
        if self.topic_slug is not None and not self.topic_slug.strip():
            raise ValueError("topic_slug cannot be blank")
        if self.started_at.tzinfo is None:
            raise ValueError("started_at must be timezone-aware")
        if self.last_activity_at.tzinfo is None:
            raise ValueError("last_activity_at must be timezone-aware")
        if self.last_activity_at < self.started_at:
            raise ValueError("last_activity_at cannot be before started_at")
        if self.time_spent_seconds < 0:
            raise ValueError("time_spent_seconds cannot be negative")
        if self.current_mcq_score is not None and (
            self.current_mcq_score < 0 or self.current_mcq_score > 100
        ):
            raise ValueError("current_mcq_score must be between 0 and 100")

    def to_memory_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "user_id": str(self.user_id),
            "subject_code": self.subject_code,
            "topic_slug": self.topic_slug,
            "started_at": self.started_at.isoformat(),
            "last_activity_at": self.last_activity_at.isoformat(),
            "time_spent_seconds": self.time_spent_seconds,
            "current_mcq_score": self.current_mcq_score,
        }

    @classmethod
    def from_memory_dict(cls, value: dict[str, object]) -> StudySession:
        return cls(
            session_id=str(value["session_id"]),
            user_id=UUID(str(value["user_id"])),
            subject_code=str(value["subject_code"]),
            topic_slug=_optional_string(value.get("topic_slug")),
            started_at=datetime.fromisoformat(str(value["started_at"])),
            last_activity_at=datetime.fromisoformat(str(value["last_activity_at"])),
            time_spent_seconds=int(value.get("time_spent_seconds", 0)),
            current_mcq_score=_optional_int(value.get("current_mcq_score")),
        )


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)
