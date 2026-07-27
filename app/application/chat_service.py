from __future__ import annotations

import logging
import re
import time
from collections import defaultdict
from typing import Any
from uuid import UUID

from app.agents.contracts import Intent, Subject
from app.agents.master_agent import MasterAgent
from app.agents.polity_agent import PolityAgent
from app.application.curriculum_service import CurriculumService
from app.application.quiz_service import QuizService

logger = logging.getLogger(__name__)

# Maximum number of conversation messages to retain per user
_MAX_HISTORY_SIZE = 20
# Number of recent messages to pass to LLM context
_LLM_HISTORY_WINDOW = 10


class ChatService:
    def __init__(
        self,
        master_agent: MasterAgent,
        polity_agent: PolityAgent,
        curriculum_service: CurriculumService,
        quiz_service: QuizService | None = None,
    ) -> None:
        self._master_agent = master_agent
        self._polity_agent = polity_agent
        self._curriculum_service = curriculum_service
        self._quiz_service = quiz_service
        # Per-user conversation history: user_id -> list of {"role": ..., "content": ...}
        self._conversation_history: dict[UUID, list[dict[str, str]]] = defaultdict(list)
        # Track the current topic the user is studying for context-aware routing
        self._current_topic: dict[UUID, str] = {}

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

        local_response = await self._try_handle_local_curriculum_request(user_id, message)
        if local_response is not None:
            logger.info("chat_complete_local user_id=%s session_id=%s", user_id, session_id)
            self._record_conversation(user_id, message, local_response.get("answer", ""))
            return local_response

        # The LLM router in MasterAgent will now handle follow-up detection
        # by returning Intent.FOLLOW_UP when appropriate.

        # 1. Route the request — pass current topic context for smarter routing
        current_topic = self._current_topic.get(user_id, "")
        try:
            command = await self._master_agent.route_request(
                message=message,
                user_id=user_id,
                session_id=session_id,
                current_topic=current_topic,
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

            if command.intent == Intent.GENERATE_MCQ:
                logger.info("chat_dispatch target=mcq_prompt user_id=%s topic=%s", user_id, topic)
                response = {
                    "answer": f"I can definitely help you test your knowledge on {topic}. Would you like me to generate a 5-question quiz for you?",
                    "subject": "Polity",
                    "topic": topic,
                    "sources": [],
                    "next_actions": [f"Generate MCQs on {topic}"],
                }
                self._record_conversation(user_id, message, response["answer"])
                return response

            if command.intent == Intent.FOLLOW_UP:
                logger.info("chat_dispatch target=polity.followup user_id=%s", user_id)
                try:
                    result = await self._teach_with_context(user_id, "auto", message)
                except Exception:
                    logger.exception("chat_dispatch_failed target=polity.followup user_id=%s", user_id)
                    raise
                self._record_conversation(user_id, message, result.get("answer", ""))
                return result

            # Default to teach for all other intents (including Teach, Explain, Compare, etc.)
            logger.info("chat_dispatch target=polity.teach user_id=%s topic=%s", user_id, topic)
            try:
                result = await self._teach_with_context(user_id, topic, message)
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
            self._record_conversation(user_id, message, result.get("answer", ""))
            return result

        # If the subject is UNKNOWN or any non-Polity subject but the user is currently
        # studying a Polity topic, treat it as an in-context Polity question rather than rejecting.
        # This fixes the "What is East India Company?" problem — when the user is studying
        # "Background to British Rule" in Polity, a question about EIC is contextually Polity.
        if current_topic:
            logger.info(
                "chat_dispatch target=polity.contextual_fallback user_id=%s subject=%s current_topic=%s",
                user_id,
                command.subject,
                current_topic,
            )
            result = await self._teach_with_context(user_id, "auto", message)
            result["next_actions"] = [
                "Show my progress",
                "Show next 3 items",
                "Mark current item complete",
            ]
            self._record_conversation(user_id, message, result.get("answer", ""))
            return result

        if command.subject == Subject.UNKNOWN:
            logger.info("chat_dispatch target=polity.contextual_fallback user_id=%s", user_id)
            result = await self._teach_with_context(user_id, "auto", message)
            result["next_actions"] = [
                "Show my progress",
                "Show next 3 items",
                "Mark current item complete",
            ]
            self._record_conversation(user_id, message, result.get("answer", ""))
            return result

        # 3. Fallback for truly unrelated subjects when the user has no active topic context
        logger.info(
            "chat_fallback user_id=%s subject=%s intent=%s duration_ms=%.2f",
            user_id,
            command.subject,
            command.intent,
            (time.perf_counter() - start_time) * 1000,
        )
        response = {
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
        self._record_conversation(user_id, message, response["answer"])
        return response

    # ---- Conversation History Management ----

    def _record_conversation(self, user_id: UUID, user_message: str, assistant_response: str) -> None:
        """Record a conversation exchange for context-aware follow-ups."""
        history = self._conversation_history[user_id]
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": assistant_response})
        # Trim to keep only the most recent messages
        if len(history) > _MAX_HISTORY_SIZE * 2:
            self._conversation_history[user_id] = history[-_MAX_HISTORY_SIZE * 2:]

    def _get_conversation_history(self, user_id: UUID) -> list[dict[str, str]]:
        """Get the recent conversation history for LLM context."""
        return list(self._conversation_history.get(user_id, [])[-_LLM_HISTORY_WINDOW * 2:])

    # ---- Context-Aware Teaching ----

    async def _teach_with_context(self, user_id: UUID, topic: str, message: str) -> dict[str, Any]:
        """Call polity_agent.teach() with full conversation context."""
        conversation_history = self._get_conversation_history(user_id)
        current_topic = self._current_topic.get(user_id, "")

        result = await self._polity_agent.teach(
            user_id=user_id,
            topic=topic,
            message=message,
            conversation_history=conversation_history,
            current_topic_context=current_topic,
        )

        # Update the tracked current topic from the agent's response
        resolved_topic = result.get("topic", "")
        if resolved_topic:
            self._current_topic[user_id] = resolved_topic

        return result

    # ---- Local Curriculum Request Handling ----

    async def _try_handle_local_curriculum_request(
        self,
        user_id: UUID,
        message: str,
    ) -> dict[str, Any] | None:
        normalized = " ".join(message.lower().split())

        if self._is_start_teaching_request(normalized):
            logger.info("chat_local_to_teach_auto user_id=%s", user_id)
            result = await self._teach_with_context(user_id, "auto", message)
            result["next_actions"] = [
                "Show next 3 items",
                "Show current module tree",
                "Mark current item complete",
            ]
            return result

        if self._is_completion_request(normalized):
            result = await self._curriculum_service.complete_current_learning_item(user_id, "polity")
            completed = result["completed"]
            next_item = result["next"]
            if completed is None:
                answer = "I could not find a current curriculum item to mark complete yet."
            elif next_item is None or next_item["node_id"] == completed["node_id"]:
                answer = f"Marked **{completed['title']}** complete. You have completed the available curriculum."
            else:
                answer = (
                    f"Marked **{completed['title']}** complete.\n\n"
                    f"Next item: **{next_item['title']}** ({next_item['level']})."
                )
            return {
                "answer": answer,
                "subject": "polity",
                "topic": next_item["title"] if next_item else None,
                "sources": [],
                "next_actions": ["Start teaching", "Show next 3 items", "Show my progress"],
            }

        next_count = self._extract_next_count(normalized)
        if next_count is not None:
            items = await self._curriculum_service.get_next_learning_items(
                user_id,
                "polity",
                count=next_count,
            )
            answer = self._format_next_items_answer(items)
            return {
                "answer": answer,
                "subject": "polity",
                "topic": items[0]["title"] if items else None,
                "sources": [],
                "next_actions": ["Start teaching", "Show current module tree", "Show my progress"],
            }

        if self._is_current_tree_request(normalized):
            tree = await self._curriculum_service.get_current_module_tree(user_id, "polity")
            answer = self._format_tree_answer(tree)
            return {
                "answer": answer,
                "subject": "polity",
                "topic": tree["title"] if tree else None,
                "sources": [],
                "next_actions": ["Start teaching", "Show next 3 items", "Show my progress"],
            }

        if self._is_progress_request(normalized):
            summary = await self._curriculum_service.get_user_progress_summary(user_id, "polity")
            answer = self._format_progress_answer(summary)
            current = summary.get("current_position") or {}
            return {
                "answer": answer,
                "subject": "polity",
                "topic": current.get("title"),
                "sources": [],
                "next_actions": ["Start teaching", "Show next 3 items", "Show current module tree"],
            }

        return None

    def _is_start_teaching_request(self, normalized: str) -> bool:
        teaching_phrases = (
            "start teaching",
            "teach next",
            "teach me next",
            "continue teaching",
            "resume teaching",
            "explain next",
        )
        return any(phrase in normalized for phrase in teaching_phrases)

    def _is_completion_request(self, normalized: str) -> bool:
        completion_phrases = (
            "mark complete",
            "mark current complete",
            "complete current",
            "i am done",
            "i finished",
            "finished this",
        )
        return any(phrase in normalized for phrase in completion_phrases)

    def _extract_next_count(self, normalized: str) -> int | None:
        if "next" not in normalized:
            return None
        if not any(word in normalized for word in ("item", "items", "topic", "topics", "lesson", "lessons")):
            return None
        match = re.search(r"next\s+(\d+)", normalized)
        if match:
            return max(1, min(int(match.group(1)), 10))
        return 3

    def _is_current_tree_request(self, normalized: str) -> bool:
        return (
            any(word in normalized for word in ("tree", "structure", "outline"))
            and any(word in normalized for word in ("current", "module", "lesson", "unit"))
        )

    def _is_progress_request(self, normalized: str) -> bool:
        phrases = (
            "my progress",
            "where am i",
            "current progress",
            "current position",
            "what am i learning",
            "what have i learnt",
            "what have i learned",
        )
        return any(phrase in normalized for phrase in phrases)

    def _format_next_items_answer(self, items: list[dict[str, Any]]) -> str:
        if not items:
            return "I could not find upcoming curriculum items yet."
        lines = ["Your next learning items:"]
        for index, item in enumerate(items, start=1):
            status = str(item["status"]).replace("_", " ")
            lines.append(f"{index}. {item['title']} ({item['level']}, {status})")
        return "\n".join(lines)

    def _format_tree_answer(self, tree: dict[str, Any] | None) -> str:
        if tree is None:
            return "I could not find the current module tree yet."

        lines = [f"Current module structure: **{tree['title']}**"]

        def walk(node: dict[str, Any], depth: int = 0) -> None:
            for child in node.get("children", []):
                indent = "  " * depth
                lines.append(f"{indent}- {child['title']} ({child['level']})")
                walk(child, depth + 1)

        walk(tree)
        return "\n".join(lines)

    def _format_progress_answer(self, summary: dict[str, Any]) -> str:
        current = summary.get("current_position")
        lines = [
            f"Polity progress: {summary.get('completion_percent', 0)}% complete.",
            (
                f"Completed leaf items: {summary.get('completed_leaf_nodes', 0)}"
                f"/{summary.get('total_leaf_nodes', 0)}."
            ),
        ]
        if current:
            path = " > ".join(item["title"] for item in current.get("path", []))
            lines.append(f"Current item: **{current['title']}** ({current['level']}).")
            if path:
                lines.append(f"Path: {path}.")
        else:
            lines.append("No current curriculum position has been started yet.")
        return "\n".join(lines)
