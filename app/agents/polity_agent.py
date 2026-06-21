import logging
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from app.memory.contracts import MemoryService, SemanticObservation
from app.rag.retrieval import RetrievalService

logger = logging.getLogger(__name__)


class MCQSchema(BaseModel):
    """Schema for a single multiple-choice question."""
    stem: str = Field(description="The question text.")
    options: list[str] = Field(description="Exactly 4 options.")
    correct_option: str = Field(description="The correct option from the list.")
    explanation: str = Field(description="Explanation of why the option is correct, citing source material.")


class QuizSchema(BaseModel):
    """Schema for a collection of multiple-choice questions."""
    questions: list[MCQSchema] = Field(description="List of MCQs.")


class PolityAgent:
    def __init__(
        self,
        memory_service: MemoryService,
        retrieval_service: RetrievalService,
        model: str = "gemini-2.5-flash",
        api_key: str | None = None,
    ) -> None:
        self._memory_service = memory_service
        self._retrieval_service = retrieval_service
        self._model = model
        kwargs: dict[str, object] = {
            "model": model,
            "temperature": 0.2,
            "max_retries": 2,
            "timeout": 30,
        }
        if api_key:
            kwargs["api_key"] = api_key

        try:
            self._llm = ChatGoogleGenerativeAI(**kwargs)
        except TypeError:
            if api_key:
                kwargs.pop("api_key", None)
                kwargs["google_api_key"] = api_key
            self._llm = ChatGoogleGenerativeAI(**kwargs)

        self._quiz_llm = self._llm.with_structured_output(QuizSchema)
        logger.info("polity_agent_initialized provider=gemini model=%s api_key_configured=%s", model, bool(api_key))

    async def teach(
        self,
        user_id: UUID,
        topic: str,
        message: str | None = None,
    ) -> dict[str, Any]:
        logger.info("polity_teach_start provider=gemini user_id=%s topic=%s message_length=%s", user_id, topic, len(message or ""))
        start_time = time.perf_counter()
        
        # 1. Get learning context
        topic_slug = topic.lower().replace(" ", "-")
        logger.info("polity_teach_context_start user_id=%s topic_slug=%s", user_id, topic_slug)
        context = await self._memory_service.get_learning_context(
            user_id=user_id,
            subject_code="polity",
            topic_slug=topic_slug,
        )
        logger.info(
            "polity_teach_context_complete user_id=%s topic_slug=%s has_progress=%s weak_topic_count=%s",
            user_id,
            topic_slug,
            bool(context.progress),
            len(context.weak_topics),
        )

        # 2. Retrieve source material
        logger.info("polity_teach_retrieval_start user_id=%s topic=%s limit=3", user_id, topic)
        retrieval_response = await self._retrieval_service.retrieve(
            query=topic,
            subject="Polity",
            limit=3,
        )
        logger.info(
            "polity_teach_retrieval_complete user_id=%s topic=%s chunk_count=%s",
            user_id,
            topic,
            len(retrieval_response.chunks),
        )

        # 3. Build Prompt
        system_prompt = self._build_teaching_system_prompt(context, retrieval_response.chunks)
        user_message = message or f"Teach me about {topic}."

        # 4. Generate Answer
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        
        try:
            logger.info("polity_teach_llm_start provider=gemini user_id=%s topic=%s model=%s", user_id, topic, self._model)
            response = await self._llm.ainvoke(messages)
            latency = time.perf_counter() - start_time
            logger.info(
                "polity_teach_llm_complete provider=gemini user_id=%s topic=%s model=%s duration_ms=%.2f response_length=%s",
                user_id,
                topic,
                self._model,
                latency * 1000,
                len(str(response.content)),
            )
        except Exception:
            logger.exception("polity_teach_llm_failed provider=gemini user_id=%s topic=%s model=%s", user_id, topic, self._model)
            raise

        # 5. Record Learning Event
        await self._memory_service.add_semantic_observation(
            SemanticObservation(
                user_id=user_id,
                subject_code="polity",
                topic_slug=topic_slug,
                observation=f"Taught topic: {topic}. User requested: {message or 'initial explanation'}",
                created_at=datetime.now(timezone.utc),
            )
        )
        logger.info(
            "polity_teach_complete user_id=%s topic=%s source_count=%s duration_ms=%.2f",
            user_id,
            topic,
            len(retrieval_response.chunks),
            (time.perf_counter() - start_time) * 1000,
        )

        return {
            "answer": response.content,
            "sources": [
                {
                    "title": chunk.metadata.get("title", "Source Material"),
                    "chapter": chunk.chapter,
                    "page_start": chunk.page_start,
                }
                for chunk in retrieval_response.chunks
            ],
            "topic": topic,
            "subject": "Polity",
            "next_actions": [
                f"Generate MCQs on {topic}",
                f"Explain {topic} in more detail",
            ],
        }

    async def generate_mcqs(
        self,
        user_id: UUID,
        topic: str,
        count: int = 5,
    ) -> QuizSchema:
        logger.info("polity_generate_mcqs_start provider=gemini user_id=%s topic=%s count=%s", user_id, topic, count)
        start_time = time.perf_counter()
        
        # 1. Get context
        topic_slug = topic.lower().replace(" ", "-")
        logger.info("polity_generate_mcqs_context_start user_id=%s topic_slug=%s", user_id, topic_slug)
        context = await self._memory_service.get_learning_context(
            user_id=user_id,
            subject_code="polity",
            topic_slug=topic_slug,
        )
        logger.info(
            "polity_generate_mcqs_context_complete user_id=%s topic_slug=%s has_progress=%s weak_topic_count=%s",
            user_id,
            topic_slug,
            bool(context.progress),
            len(context.weak_topics),
        )

        # 2. Retrieve source material
        logger.info("polity_generate_mcqs_retrieval_start user_id=%s topic=%s limit=5", user_id, topic)
        retrieval_response = await self._retrieval_service.retrieve(
            query=f"MCQs on {topic}",
            subject="Polity",
            limit=5,
        )
        logger.info(
            "polity_generate_mcqs_retrieval_complete user_id=%s topic=%s chunk_count=%s",
            user_id,
            topic,
            len(retrieval_response.chunks),
        )

        # 3. Build Prompt
        system_prompt = (
            "You are the Polity Examiner at AI University. Your goal is to generate high-quality "
            "multiple-choice questions for the UPSC Civil Services Examination.\n\n"
            f"TOPIC: {topic}\n"
            f"SOURCE MATERIAL:\n"
            + "\n\n".join([c.content for c in retrieval_response.chunks])
            + "\n\nINSTRUCTIONS:\n"
            f"1. Generate {count} MCQs.\n"
            "2. Questions must be analytical and ground in the source material.\n"
            "3. Provide 4 distinct options for each question.\n"
            "4. Provide a clear explanation citing the source material for the correct answer."
        )

        # 4. Generate
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Generate {count} MCQs on {topic}."),
        ]
        
        try:
            logger.info("polity_generate_mcqs_llm_start provider=gemini user_id=%s topic=%s model=%s count=%s", user_id, topic, self._model, count)
            result = await self._quiz_llm.ainvoke(messages)
            latency = time.perf_counter() - start_time
            logger.info(
                "polity_generate_mcqs_llm_complete provider=gemini user_id=%s topic=%s model=%s generated_questions=%s duration_ms=%.2f",
                user_id,
                topic,
                self._model,
                len(result.questions),
                latency * 1000,
            )
            return result
        except Exception:
            logger.exception("polity_generate_mcqs_llm_failed provider=gemini user_id=%s topic=%s model=%s count=%s", user_id, topic, self._model, count)
            raise

    async def evaluate_mcq_submission(
        self,
        user_id: UUID,
        topic: str,
        score: int,
        total: int,
        weak_topics: list[str],
    ) -> str:
        """Generate personalized feedback for an MCQ attempt."""
        logger.info(
            "polity_evaluate_mcq_start provider=gemini user_id=%s topic=%s score=%s total=%s weak_topic_count=%s",
            user_id,
            topic,
            score,
            total,
            len(weak_topics),
        )
        start_time = time.perf_counter()
        
        system_prompt = (
            "You are the Polity Mentor at AI University. Provide concise, encouraging, "
            "and analytical feedback on a student's MCQ performance.\n\n"
            f"STUDENT PERFORMANCE:\n"
            f"- Topic: {topic}\n"
            f"- Score: {score}/{total}\n"
            f"- Identified Weak Areas: {', '.join(weak_topics) if weak_topics else 'None'}"
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="Provide personalized feedback and next steps."),
        ]
        
        try:
            logger.info("polity_evaluate_mcq_llm_start provider=gemini user_id=%s topic=%s model=%s", user_id, topic, self._model)
            response = await self._llm.ainvoke(messages)
            latency = time.perf_counter() - start_time
            logger.info(
                "polity_evaluate_mcq_llm_complete provider=gemini user_id=%s topic=%s model=%s duration_ms=%.2f response_length=%s",
                user_id,
                topic,
                self._model,
                latency * 1000,
                len(str(response.content)),
            )
            return response.content
        except Exception:
            logger.exception("polity_evaluate_mcq_llm_failed provider=gemini user_id=%s topic=%s model=%s fallback=true", user_id, topic, self._model)
            return "Good attempt. Review your weak areas and keep practicing."

    def _build_teaching_system_prompt(self, context: Any, chunks: list[Any]) -> str:
        # ... (rest of the method)
        # Context summary
        progress_info = "New topic for the user."
        if context.progress:
            progress_info = (
                f"User has {context.progress.completion_percent}% completion "
                f"and {context.progress.confidence_score}/10 confidence."
            )
        
        weak_areas = ", ".join(context.weak_topics) if context.weak_topics else "None identified yet."
        
        # Source chunks
        sources_text = "\n\n".join([
            f"SOURCE CHUNK (Chapter: {c.chapter}, Page: {c.page_start}):\n{c.content}"
            for c in chunks
        ])

        return (
            "You are the Polity Expert at AI University. Your goal is to teach Indian Polity "
            "for the UPSC Civil Services Examination. Use a professional, clear, and analytical tone.\n\n"
            f"USER CONTEXT:\n- {progress_info}\n- Weak Areas: {weak_areas}\n\n"
            f"SOURCE MATERIAL:\n{sources_text}\n\n"
            "INSTRUCTIONS:\n"
            "1. Ground your answer strictly in the provided source material.\n"
            "2. If the user has weak areas, try to clarify those points if relevant.\n"
            "3. Use UPSC-style analysis (importance, constitutional provisions, implications).\n"
            "4. Cite sources in your text (e.g., 'As per the chapter on Fundamental Rights...').\n"
            "5. If the source material is insufficient, state what you know generally but prioritize sources."
        )
