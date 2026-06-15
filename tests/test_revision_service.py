import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.domain.learning import Assessment, AssessmentType, RevisionStatus
from app.application.revision_service import RevisionService


@pytest.mark.asyncio
async def test_revision_service_plans_tasks_for_low_score():
    memory_service = AsyncMock()
    service = RevisionService(memory_service)
    
    user_id = uuid4()
    topic_id = uuid4()
    assessment = Assessment(
        user_id=user_id,
        topic_id=topic_id,
        assessment_type=AssessmentType.MCQ,
        score=2,
        total=10, # 20% - should trigger revision
        submitted_at=datetime.now(timezone.utc),
    )
    
    tasks = await service.plan_revisions_for_assessment(assessment)
    
    assert len(tasks) == 3
    assert tasks[0].due_at > datetime.now(timezone.utc)
    memory_service.create_revision_tasks.assert_called_once_with(tasks)


@pytest.mark.asyncio
async def test_revision_service_plans_no_tasks_for_high_score():
    memory_service = AsyncMock()
    service = RevisionService(memory_service)
    
    user_id = uuid4()
    topic_id = uuid4()
    assessment = Assessment(
        user_id=user_id,
        topic_id=topic_id,
        assessment_type=AssessmentType.MCQ,
        score=9,
        total=10, # 90% - should NOT trigger revision
        submitted_at=datetime.now(timezone.utc),
    )
    
    tasks = await service.plan_revisions_for_assessment(assessment)
    
    assert len(tasks) == 0
    memory_service.create_revision_tasks.assert_not_called()
