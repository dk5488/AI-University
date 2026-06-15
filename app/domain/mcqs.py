from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class MCQOption:
    content: str
    is_correct: bool = False


@dataclass(frozen=True, slots=True)
class MCQ:
    stem: str
    options: tuple[MCQOption, ...]
    explanation: str | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.stem.strip():
            raise ValueError("MCQ stem is required")
        if len(self.options) < 2:
            raise ValueError("MCQ must have at least 2 options")
        if sum(1 for opt in self.options if opt.is_correct) != 1:
            raise ValueError("MCQ must have exactly one correct option")


@dataclass(frozen=True, slots=True)
class Quiz:
    topic_id: UUID
    questions: tuple[MCQ, ...]
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.questions:
            raise ValueError("Quiz must have at least one question")


@dataclass(frozen=True, slots=True)
class UserAnswer:
    question_id: UUID
    selected_option: str


@dataclass(frozen=True, slots=True)
class MCQSubmission:
    user_id: UUID
    quiz_id: UUID
    answers: tuple[UserAnswer, ...]
