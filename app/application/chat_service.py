from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from app.agents.contracts import Intent, Subject
from app.agents.master_agent import MasterAgent
from app.agents.polity_agent import PolityAgent
from app.application.quiz_service import QuizService

logger = logging.getLogger(__name__)


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
        start_time = time.perf_counter()
        logger.info(
            "chat_start user_id=%s session_id=%s message_length=%s",
            user_id,
            session_id,
            len(message),
        )

        # 1. Route the request
        try:
            command = await self._master_agent.route_request(
                message=message,
                user_id=user_id,
                session_id=session_id,
            )
        except Exception:
            logger.exception("chat_route_failed user_id=%s session_id=%s", user_id, session_id)
            raise

        logger.info(
            "chat_routed user_id=%s subject=%s intent=%s topic=%s confidence=%.2f",
            user_id,
            command.subject,
            command.intent,
            command.topic,
            command.confidence,
        )

        # 2. Execute based on subject and intent
        if command.subject == Subject.POLITY:
            topic = command.topic or "Polity"
            
            if command.intent == Intent.TEACH:
                logger.info("chat_dispatch target=polity.teach user_id=%s topic=%s", user_id, topic)
                try:
                    result = await self._polity_agent.teach(
                        user_id=user_id,
                        topic=topic,
                        message=message,
                    )
                except Exception:
                    logger.exception("chat_dispatch_failed target=polity.teach user_id=%s topic=%s", user_id, topic)
                    raise
                logger.info(
                    "chat_complete user_id=%s subject=%s intent=%s duration_ms=%.2f",
                    user_id,
                    command.subject,
                    command.intent,
                    (time.perf_counter() - start_time) * 1000,
                )
                return result
            
            if command.intent == Intent.GENERATE_MCQ:
                logger.info("chat_dispatch target=mcq_prompt user_id=%s topic=%s", user_id, topic)
                return {
                    "answer": f"I can definitely help you test your knowledge on {topic}. Would you like me to generate a 5-question quiz for you?",
                    "subject": "Polity",
                    "topic": topic,
                    "sources": [],
                    "next_actions": [f"Generate MCQs on {topic}"],
                }
            
            # Future: Handle other intents
        
        # 3. Fallback for unknown or unsupported subjects
        logger.info(
            "chat_fallback user_id=%s subject=%s intent=%s duration_ms=%.2f",
            user_id,
            command.subject,
            command.intent,
            (time.perf_counter() - start_time) * 1000,
        )
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
