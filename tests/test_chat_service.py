from uuid import uuid4

import pytest

from app.application.chat_service import ChatService
from app.application.curriculum_service import CurriculumService
from app.memory.in_memory import create_in_memory_memory_service
from tests.test_curriculum_progress import sample_curriculum


class UnusedMasterAgent:
    async def route_request(self, *args, **kwargs):  # pragma: no cover
        raise AssertionError("local curriculum requests should not call the router")


class FakePolityAgent:
    async def teach(self, user_id, topic, message=None, conversation_history=None, current_topic_context=None):
        return {
            "answer": f"Teaching {topic}: {message}",
            "subject": "Polity",
            "topic": topic,
            "sources": [],
            "next_actions": [],
        }


@pytest.mark.asyncio
async def test_chat_service_handles_next_items_locally() -> None:
    memory_service = create_in_memory_memory_service()
    await memory_service.store_curriculum("polity", sample_curriculum())
    curriculum_service = CurriculumService(memory_service, api_key="dummy")
    service = ChatService(
        master_agent=UnusedMasterAgent(),
        polity_agent=FakePolityAgent(),
        curriculum_service=curriculum_service,
    )

    result = await service.chat(uuid4(), "what are next 2 items in the course")

    assert "Historical Acts" in result["answer"]
    assert "Constituent Assembly" in result["answer"]
    assert result["sources"] == []


@pytest.mark.asyncio
async def test_chat_service_sends_start_teaching_to_polity_agent() -> None:
    memory_service = create_in_memory_memory_service()
    await memory_service.store_curriculum("polity", sample_curriculum())
    curriculum_service = CurriculumService(memory_service, api_key="dummy")
    service = ChatService(
        master_agent=UnusedMasterAgent(),
        polity_agent=FakePolityAgent(),
        curriculum_service=curriculum_service,
    )

    result = await service.chat(uuid4(), "start teaching")

    assert "Teaching auto" in result["answer"]
    assert "Show next 3 items" in result["next_actions"]
