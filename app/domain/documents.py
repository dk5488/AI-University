from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4


class SourceType(StrEnum):
    PDF = "pdf"
    TEXT = "text"
    MARKDOWN = "markdown"


@dataclass(frozen=True, slots=True)
class Document:
    title: str
    source_type: SourceType
    version_hash: str
    subject_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("document title is required")
        if not self.version_hash.strip():
            raise ValueError("version_hash is required")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    document_id: UUID
    content: str
    content_hash: str
    chunk_index: int
    page_start: int | None = None
    page_end: int | None = None
    chapter: str | None = None
    topic_hint: str | None = None
    id: UUID = field(default_factory=uuid4)
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("chunk content cannot be empty")
        if not self.content_hash.strip():
            raise ValueError("content_hash is required")
        if self.chunk_index < 0:
            raise ValueError("chunk_index cannot be negative")
