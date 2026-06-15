from __future__ import annotations

from typing import Any
from uuid import UUID

from app.agents.contracts import Intent, Subject
from app.agents.master_agent import MasterAgent
from app.agents.polity_agent import PolityAgent
from app.application.quiz_service import QuizService


class ChatService:
    def __init__(
        self,
        master_agent: MasterAgent,
        polity_agent: PolityAgent,
        quiz_service: QuizService | None = None,
    ) -> None:
        self._master_agent = master_agent
        self._polity_agent = polity_agent
        self._quiz_service = quiz_service

    async def chat(
        self,
        user_id: UUID,
        message: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        # 1. Route the request
        command = await self._master_agent.route_request(
            message=message,
            user_id=user_id,
            session_id=session_id,
        )

        # 2. Execute based on subject and intent
        if command.subject == Subject.POLITY:
            topic = command.topic or "Polity"
            
            if command.intent == Intent.TEACH:
                return await self._polity_agent.teach(
                    user_id=user_id,
                    topic=topic,
                    message=message,
                )
            
            if command.intent == Intent.GENERATE_MCQ:
                return {
                    "answer": f"I can definitely help you test your knowledge on {topic}. Would you like me to generate a 5-question quiz for you?",
                    "subject": "Polity",
                    "topic": topic,
                    "sources": [],
                    "next_actions": [f"Generate MCQs on {topic}"],
                }
            
            # Future: Handle other intents
        
        # 3. Fallback for unknown or unsupported subjects
        return {
            "answer": (
                "I understand you're interested in "
                f"{command.subject if command.subject != Subject.UNKNOWN else 'this topic'}, "
                "but I'm currently only specialized in Indian Polity teaching. "
                "How can I help you with Polity today?"
            ),
            "subject": command.subject,
            "intent": command.intent,
            "topic": command.topic,
            "sources": [],
        }
