from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.learning import Assessment, AssessmentType, Progress, RevisionTask


def test_progress_rejects_invalid_completion() -> None:
    with pytest.raises(ValueError, match="completion_percent"):
        Progress(
            user_id=uuid4(),
            topic_id=uuid4(),
            completion_percent=101,
            confidence_score=5,
        )


def test_assessment_percentage_is_derived_from_score() -> None:
    assessment = Assessment(
        user_id=uuid4(),
        topic_id=uuid4(),
        assessment_type=AssessmentType.MCQ,
        score=4,
        total=10,
        submitted_at=datetime(2026, 6, 15, tzinfo=UTC),
        weak_topics=("Writs",),
    )

    assert assessment.percentage == 40


def test_assessment_rejects_naive_submission_time() -> None:
    with pytest.raises(ValueError, match="submitted_at"):
        Assessment(
            user_id=uuid4(),
            topic_id=uuid4(),
            assessment_type=AssessmentType.MCQ,
            score=4,
            total=10,
            submitted_at=datetime(2026, 6, 15),
        )


def test_revision_task_complete_returns_completed_copy() -> None:
    task = RevisionTask(
        user_id=uuid4(),
        topic_id=uuid4(),
        due_at=datetime(2026, 6, 16, tzinfo=UTC),
        reason="Low MCQ score",
    )

    completed = task.complete(datetime(2026, 6, 16, 9, tzinfo=UTC))

    assert completed.id == task.id
    assert completed.status == "completed"
    assert completed.completed_at == datetime(2026, 6, 16, 9, tzinfo=UTC)
