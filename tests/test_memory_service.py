from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.learning import Assessment, AssessmentType
from app.memory.contracts import ProgressUpdate, SemanticObservation
from app.memory.in_memory import create_in_memory_memory_service


@pytest.mark.asyncio
async def test_memory_service_builds_learning_context() -> None:
    service = create_in_memory_memory_service()
    user_id = uuid4()
    topic_id = uuid4()

    await service.record_progress(
        ProgressUpdate(
            user_id=user_id,
            topic_id=topic_id,
            completion_percent=80,
            confidence_score=6,
            last_studied_at=datetime(2026, 6, 12, tzinfo=UTC),
        )
    )
    await service.record_assessment(
        Assessment(
            user_id=user_id,
            topic_id=topic_id,
            assessment_type=AssessmentType.MCQ,
            score=4,
            total=10,
            submitted_at=datetime(2026, 6, 15, tzinfo=UTC),
            weak_topics=("Writs", "DPSP"),
        )
    )
    await service.add_semantic_observation(
        SemanticObservation(
            user_id=user_id,
            subject_code="polity",
            topic_slug="fundamental-rights",
            observation="User confuses DPSP with Fundamental Rights",
            created_at=datetime(2026, 6, 15, tzinfo=UTC),
        )
    )

    context = await service.get_learning_context(
        user_id=user_id,
        subject_code="polity",
        topic_id=topic_id,
        topic_slug="fundamental-rights",
    )

    assert context.progress is not None
    assert context.progress.completion_percent == 80
    assert context.weak_topics == ("Writs", "DPSP")
    assert context.last_studied_at == datetime(2026, 6, 12, tzinfo=UTC)
    assert context.semantic_observations == (
        "User confuses DPSP with Fundamental Rights",
    )


@pytest.mark.asyncio
async def test_memory_service_session_round_trip_and_clear() -> None:
    service = create_in_memory_memory_service()
    user_id = uuid4()

    await service.set_session(
        user_id,
        "session-1",
        {"subject": "Economy", "time_spent_seconds": 5400},
        ttl_seconds=60,
    )

    assert await service.get_session(user_id, "session-1") == {
        "subject": "Economy",
        "time_spent_seconds": 5400,
    }

    await service.clear_session(user_id, "session-1")

    assert await service.get_session(user_id, "session-1") is None
