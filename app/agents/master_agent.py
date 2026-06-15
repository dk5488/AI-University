from __future__ import annotations

from typing import Annotated, Literal, TypedDict
from uuid import UUID

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from app.agents.contracts import Intent, RoutedCommand, Subject


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
    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None) -> None:
        self._llm = ChatOpenAI(model=model, api_key=api_key)
        self._router_llm = self._llm.with_structured_output(RouteSchema)
        self._graph = self._build_graph()

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
            "If the request is ambiguous, use Unknown for subject/intent."
        )
        
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        route = await self._router_llm.ainvoke(messages)
        return {"route": route}

    async def route_request(
        self,
        message: str,
        user_id: UUID | None = None,
        session_id: str | None = None,
    ) -> RoutedCommand:
        state: AgentState = {
            "messages": [HumanMessage(content=message)],
            "route": None,
            "user_id": user_id,
            "session_id": session_id,
        }
        
        result = await self._graph.ainvoke(state)
        route: RouteSchema = result["route"]
        
        return RoutedCommand(
            subject=route.subject,
            intent=route.intent,
            topic=route.topic,
            confidence=route.confidence,
            original_message=message,
            user_id=user_id,
            session_id=session_id,
        )
