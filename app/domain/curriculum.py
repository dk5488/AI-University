from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class CurriculumLevel(StrEnum):
    PREPARATION = "preparation"
    PHASE = "phase"
    MODULE = "module"
    UNIT = "unit"
    CHAPTER = "chapter"
    TOPIC = "topic"
    CONCEPT = "concept"


class NodeStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class CurriculumNode:
    """A single node in the hierarchical teaching structure."""

    id: str
    parent_id: str | None
    level: CurriculumLevel
    title: str
    subject_code: str
    learning_order: int
    prerequisites: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    child_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("id is required")
        if not self.title.strip():
            raise ValueError("title is required")
        if not self.subject_code.strip():
            raise ValueError("subject_code is required")
        if self.learning_order < 0:
            raise ValueError("learning_order cannot be negative")


@dataclass(frozen=True, slots=True)
class CurriculumProgress:
    """Tracks a user's progress on a specific curriculum node."""

    user_id: UUID
    node_id: str
    status: NodeStatus = NodeStatus.NOT_STARTED
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("node_id is required")
        if self.status == NodeStatus.COMPLETED and self.completed_at is None:
            raise ValueError("completed_at is required for completed nodes")
        if self.status == NodeStatus.NOT_STARTED and self.started_at is not None:
            raise ValueError("started_at must be None for not_started nodes")

    def start(self, started_at: datetime) -> CurriculumProgress:
        return CurriculumProgress(
            user_id=self.user_id,
            node_id=self.node_id,
            status=NodeStatus.IN_PROGRESS,
            started_at=started_at,
            completed_at=None,
        )

    def complete(self, completed_at: datetime) -> CurriculumProgress:
        return CurriculumProgress(
            user_id=self.user_id,
            node_id=self.node_id,
            status=NodeStatus.COMPLETED,
            started_at=self.started_at,
            completed_at=completed_at,
        )
