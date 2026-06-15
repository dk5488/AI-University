from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class Intent(StrEnum):
    TEACH = "teach"
    GENERATE_MCQ = "generate_mcq"
    EVALUATE_MCQ = "evaluate_mcq"
    REVISE = "revise"
    EXPLAIN = "explain"
    COMPARE = "compare"
    UNKNOWN = "unknown"


class Subject(StrEnum):
    POLITY = "polity"
    HISTORY = "history"
    ECONOMY = "economy"
    CURRENT_AFFAIRS = "current_affairs"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class RoutedCommand:
    subject: Subject
    intent: Intent
    topic: str | None = None
    confidence: float = 0.0
    original_message: str = ""
    user_id: UUID | None = None
    session_id: str | None = None
