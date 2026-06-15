from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.session_service import StartStudySessionCommand, StudySessionService
from app.memory.in_memory import create_in_memory_memory_service


@pytest.mark.asyncio
async def test_study_session_service_starts_and_ends_session() -> None:
    memory_service = create_in_memory_memory_service()
    service = StudySessionService(memory_service)
    user_id = uuid4()

    started = await service.start_session(
        StartStudySessionCommand(
            user_id=user_id,
            subject_code="polity",
            topic_slug="fundamental-rights",
            started_at=datetime(2026, 6, 15, 10, tzinfo=UTC),
        )
    )

    fetched = await service.get_session(user_id, started.session_id)
    ended = await service.end_session(user_id, started.session_id)

    assert fetched == started
    assert ended == started
    assert await service.get_session(user_id, started.session_id) is None
