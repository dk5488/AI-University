from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.curriculum_service import CurriculumService
from app.domain.curriculum import CurriculumLevel, CurriculumNode, NodeStatus
from app.memory.in_memory import create_in_memory_memory_service


def sample_curriculum() -> list[CurriculumNode]:
    return [
        CurriculumNode(
            id="prep",
            parent_id=None,
            level=CurriculumLevel.PREPARATION,
            title="Indian Polity Preparation",
            subject_code="polity",
            learning_order=1,
            child_ids=("phase-foundation",),
        ),
        CurriculumNode(
            id="phase-foundation",
            parent_id="prep",
            level=CurriculumLevel.PHASE,
            title="Foundation",
            subject_code="polity",
            learning_order=2,
            child_ids=("module-constitution",),
        ),
        CurriculumNode(
            id="module-constitution",
            parent_id="phase-foundation",
            level=CurriculumLevel.MODULE,
            title="Constitutional Foundations",
            subject_code="polity",
            learning_order=3,
            child_ids=("unit-history",),
        ),
        CurriculumNode(
            id="unit-history",
            parent_id="module-constitution",
            level=CurriculumLevel.UNIT,
            title="Historical Background",
            subject_code="polity",
            learning_order=4,
            child_ids=("topic-acts", "topic-assembly", "topic-preamble"),
        ),
        CurriculumNode(
            id="topic-acts",
            parent_id="unit-history",
            level=CurriculumLevel.TOPIC,
            title="Historical Acts",
            subject_code="polity",
            learning_order=5,
        ),
        CurriculumNode(
            id="topic-assembly",
            parent_id="unit-history",
            level=CurriculumLevel.TOPIC,
            title="Constituent Assembly",
            subject_code="polity",
            learning_order=6,
        ),
        CurriculumNode(
            id="topic-preamble",
            parent_id="unit-history",
            level=CurriculumLevel.TOPIC,
            title="Preamble",
            subject_code="polity",
            learning_order=7,
        ),
    ]


@pytest.mark.asyncio
async def test_curriculum_service_tracks_current_and_next_items() -> None:
    memory_service = create_in_memory_memory_service()
    await memory_service.store_curriculum("polity", sample_curriculum())
    service = CurriculumService(memory_service, api_key="dummy")
    user_id = uuid4()

    await memory_service.upsert_curriculum_progress(
        user_id,
        "topic-acts",
        NodeStatus.COMPLETED,
        started_at=datetime(2026, 7, 7, tzinfo=UTC),
        completed_at=datetime(2026, 7, 7, 1, tzinfo=UTC),
    )
    await memory_service.upsert_curriculum_progress(
        user_id,
        "topic-assembly",
        NodeStatus.IN_PROGRESS,
        started_at=datetime(2026, 7, 7, 2, tzinfo=UTC),
    )

    summary = await service.get_user_progress_summary(user_id, "polity")
    next_items = await service.get_next_learning_items(user_id, "polity", count=2)
    tree = await service.get_current_module_tree(user_id, "polity")

    assert summary["completed_leaf_nodes"] == 1
    assert summary["current_position"]["node_id"] == "topic-assembly"
    assert next_items[0]["node_id"] == "topic-assembly"
    assert next_items[1]["node_id"] == "topic-preamble"
    assert tree is not None
    assert tree["id"] == "module-constitution"


@pytest.mark.asyncio
async def test_curriculum_service_marks_current_item_complete() -> None:
    memory_service = create_in_memory_memory_service()
    await memory_service.store_curriculum("polity", sample_curriculum())
    service = CurriculumService(memory_service, api_key="dummy")
    user_id = uuid4()

    result = await service.complete_current_learning_item(user_id, "polity")

    assert result["completed"]["node_id"] == "topic-acts"
    assert result["next"]["node_id"] == "topic-assembly"
