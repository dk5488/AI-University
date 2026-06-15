import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.agents.master_agent import MasterAgent, RouteSchema
from app.agents.contracts import Intent, Subject


@pytest.mark.asyncio
async def test_master_agent_routes_polity_teach():
    # Mock the LLM with structured output
    mock_llm = MagicMock()
    mock_router = AsyncMock()
    mock_router.ainvoke.return_value = RouteSchema(
        subject=Subject.POLITY,
        intent=Intent.TEACH,
        topic="Fundamental Rights",
        confidence=0.95,
    )
    
    # We need to mock the with_structured_output call
    master_agent = MasterAgent()
    master_agent._router_llm = mock_router
    
    user_id = uuid4()
    command = await master_agent.route_request(
        "Teach me Fundamental Rights",
        user_id=user_id,
    )
    
    assert command.subject == Subject.POLITY
    assert command.intent == Intent.TEACH
    assert "Fundamental Rights" in command.topic
    assert command.user_id == user_id


@pytest.mark.asyncio
async def test_master_agent_routes_mcq_generation():
    mock_router = AsyncMock()
    mock_router.ainvoke.return_value = RouteSchema(
        subject=Subject.POLITY,
        intent=Intent.GENERATE_MCQ,
        topic="Article 32",
        confidence=0.9,
    )
    
    master_agent = MasterAgent()
    master_agent._router_llm = mock_router
    
    command = await master_agent.route_request("Generate MCQs on Article 32")
    
    assert command.subject == Subject.POLITY
    assert command.intent == Intent.GENERATE_MCQ
    assert "Article 32" in command.topic
