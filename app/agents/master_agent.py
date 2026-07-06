from __future__ import annotations

import logging
import time
from typing import Annotated, Literal, TypedDict
from uuid import UUID

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from app.agents.contracts import Intent, RoutedCommand, Subject

logger = logging.getLogger(__name__)


class RouteSchema(BaseModel):
    """Schema for routing user intent to the correct subject and action."""
    subject: Subject = Field(description="The subject of the request.")
    intent: Intent = Field(description="The intent/action the user wants to perform.")
    topic: str | None = Field(description="The specific topic mentioned, if any.")
    confidence: float = Field(description="Confidence score for this routing (0.0 to 1.0).")


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], "The messages in the conversation."]
    route: RouteSchema | None
    user_id: UUID | None
    session_id: str | None


class MasterAgent:
    def __init__(self, model: str = "gemini-2.5-flash", api_key: str | None = None) -> None:
        self._model = model
        kwargs: dict[str, object] = {"model": model, "temperature": 0, "max_retries": 2}
        if api_key:
            kwargs["api_key"] = api_key

        try:
            self._llm = ChatGoogleGenerativeAI(**kwargs)
        except TypeError:
            if api_key:
                kwargs.pop("api_key", None)
                kwargs["google_api_key"] = api_key
            self._llm = ChatGoogleGenerativeAI(**kwargs)

        self._router_llm = self._llm.with_structured_output(RouteSchema)
        self._graph = self._build_graph()
        logger.info("master_agent_initialized provider=gemini model=%s api_key_configured=%s", model, bool(api_key))

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(AgentState)
        
        builder.add_node("classify", self._classify_intent)
        builder.set_entry_point("classify")
        
        # In this milestone, we only implement routing. 
        # Future milestones will add edges to subject agents.
        builder.add_edge("classify", END)
        
        return builder.compile()

    async def _classify_intent(self, state: AgentState) -> dict[str, object]:
        system_prompt = (
            "You are the Master Agent of AI University, an UPSC coaching institute. "
            "Your job is to route user requests to the correct subject expert and intent. "
            "Subjects: Polity, History, Economy, Current Affairs. "
            "Intents: Teach (learning/explaining), GenerateMCQ (creating quizzes), "
            "EvaluateMCQ (checking answers), Revise (spaced repetition), "
            "Explain (deep dive), Compare (cross-topic comparison). "
            "If the request is ambiguous, use Unknown for subject/intent. "
            "CRITICAL: If the user asks generic learning questions like 'start teaching me', "
            "'what is the next module', 'where am I', or 'teach me next', set the intent to Teach "
            "and the topic to 'auto'. This signals the subject agent to look up their progress."
        )
        
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        start_time = time.perf_counter()
        logger.info(
            "master_agent_classify_start provider=gemini model=%s user_id=%s session_id=%s message_count=%s",
            self._model,
            state.get("user_id"),
            state.get("session_id"),
            len(state["messages"]),
        )
        try:
            route = await self._router_llm.ainvoke(messages)
        except Exception:
            logger.exception(
                "master_agent_classify_failed provider=gemini model=%s user_id=%s session_id=%s",
                self._model,
                state.get("user_id"),
                state.get("session_id"),
            )
            raise
        logger.info(
            "master_agent_classify_complete provider=gemini model=%s subject=%s intent=%s topic=%s confidence=%.2f duration_ms=%.2f",
            self._model,
            route.subject,
            route.intent,
            route.topic,
            route.confidence,
            (time.perf_counter() - start_time) * 1000,
        )
        return {"route": route}

    async def route_request(
        self,
        message: str,
        user_id: UUID | None = None,
        session_id: str | None = None,
    ) -> RoutedCommand:
        start_time = time.perf_counter()
        logger.info(
            "master_agent_route_start user_id=%s session_id=%s message_length=%s",
            user_id,
            session_id,
            len(message),
        )
        state: AgentState = {
            "messages": [HumanMessage(content=message)],
            "route": None,
            "user_id": user_id,
            "session_id": session_id,
        }
        
        result = await self._graph.ainvoke(state)
        route: RouteSchema = result["route"]
        logger.info(
            "master_agent_route_complete user_id=%s subject=%s intent=%s topic=%s duration_ms=%.2f",
            user_id,
            route.subject,
            route.intent,
            route.topic,
            (time.perf_counter() - start_time) * 1000,
        )
        
        return RoutedCommand(
            subject=route.subject,
            intent=route.intent,
            topic=route.topic,
            confidence=route.confidence,
            original_message=message,
            user_id=user_id,
            session_id=session_id,
        )
