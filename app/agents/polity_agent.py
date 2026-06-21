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

    # Authoritative knowledge base references — these books are well-known
    # to the LLM, so we instruct it to draw from them by name rather than
    # requiring expensive RAG embedding/retrieval on the free tier.
    KNOWLEDGE_BASE = (
        "Your authoritative knowledge base consists of the following standard UPSC Polity resources:\n"
        "1. M. Laxmikanth - 'Indian Polity' (the definitive UPSC Polity textbook)\n"
        "2. NCERT Class 6 - Social and Political Life I\n"
        "3. NCERT Class 7 - Social and Political Life II\n"
        "4. NCERT Class 8 - Social and Political Life III\n"
        "5. NCERT Class 9 - Democratic Politics I\n"
        "6. NCERT Class 10 - Democratic Politics II\n"
        "7. NCERT Class 11 - Indian Constitution at Work\n"
        "8. NCERT Class 11 - Political Theory\n"
        "9. NCERT Class 12 - Politics in India since Independence\n"
        "10. NCERT Class 12 - Contemporary World Politics\n"
        "\n"
        "CRITICAL: You MUST ground ALL your answers in these specific sources. "
        "Always cite which book/chapter your information comes from "
        "(e.g., 'As per Laxmikanth, Chapter 5 on Fundamental Rights...' or "
        "'According to NCERT Class 11 - Indian Constitution at Work, Chapter 3...'). "
        "Do NOT use generic knowledge. Treat these books as your primary and authoritative sources."
    )

    async def teach(
        self,
        user_id: UUID,
        topic: str,
        message: str | None = None,
    ) -> dict[str, Any]:
        logger.info("polity_teach_start provider=gemini user_id=%s topic=%s message_length=%s", user_id, topic, len(message or ""))
        start_time = time.perf_counter()
        
        # 0. Handle Dynamic/Auto Topic Resolution
        resolved_topic = topic
        status_message = ""
        if topic.lower() in ("auto", "next", "status"):
            current_topic, progress = await self._memory_service.get_current_topic(user_id, "polity")
            if current_topic:
                resolved_topic = current_topic.name
                pct = progress.completion_percent if progress else 0
                if topic.lower() == "status":
                    status_message = f"You are currently on **{resolved_topic}** ({pct}% complete). "
                elif pct > 0 and pct < 100:
                    status_message = f"You haven't finished **{resolved_topic}** yet ({pct}% complete). Let's complete this before moving forward. "
                else:
                    status_message = f"Moving on to the next module: **{resolved_topic}**. "
            else:
                resolved_topic = "Historical Background"  # fallback
        
        topic_slug = resolved_topic.lower().replace(" ", "-")

        # 1. Get learning context
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

        # 2. Attempt RAG retrieval (optional enhancement — works without it)
        rag_chunks = []
        try:
            logger.info("polity_teach_retrieval_start user_id=%s topic=%s limit=3", user_id, resolved_topic)
            retrieval_response = await self._retrieval_service.retrieve(
                query=resolved_topic,
                subject="Polity",
                limit=3,
            )
            rag_chunks = retrieval_response.chunks
            logger.info(
                "polity_teach_retrieval_complete user_id=%s topic=%s chunk_count=%s",
                user_id,
                resolved_topic,
                len(rag_chunks),
            )
        except Exception:
            logger.warning("polity_teach_retrieval_skipped user_id=%s topic=%s reason=retrieval_failed", user_id, resolved_topic)

        # 3. Build Prompt (knowledge-base-aware, with optional RAG enrichment)
        system_prompt = self._build_teaching_system_prompt(context, rag_chunks, current_topic_name=resolved_topic)
        user_message = message or f"Teach me about {resolved_topic}."

        # 4. Generate Answer
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        
        try:
            logger.info("polity_teach_llm_start provider=gemini user_id=%s topic=%s model=%s", user_id, resolved_topic, self._model)
            response = await self._llm.ainvoke(messages)
            latency = time.perf_counter() - start_time
            logger.info(
                "polity_teach_llm_complete provider=gemini user_id=%s topic=%s model=%s duration_ms=%.2f response_length=%s",
                user_id,
                resolved_topic,
                self._model,
                latency * 1000,
                len(str(response.content)),
            )
        except Exception:
            logger.exception("polity_teach_llm_failed provider=gemini user_id=%s topic=%s model=%s", user_id, resolved_topic, self._model)
            raise

        # prepend status message if auto resolved
        final_answer = response.content
        if status_message:
            final_answer = status_message + "\n\n" + final_answer

        # 5. Record Learning Event
        await self._memory_service.add_semantic_observation(
            SemanticObservation(
                user_id=user_id,
                subject_code="polity",
                topic_slug=topic_slug,
                observation=f"Taught topic: {resolved_topic}. User requested: {message or 'initial explanation'}",
                created_at=datetime.now(timezone.utc),
            )
        )
        logger.info(
            "polity_teach_complete user_id=%s topic=%s source_count=%s duration_ms=%.2f",
            user_id,
            topic,
            len(rag_chunks),
            (time.perf_counter() - start_time) * 1000,
        )

        # Build source references
        sources = [
            {
                "title": chunk.metadata.get("title", "Source Material"),
                "chapter": chunk.chapter,
                "page_start": chunk.page_start,
            }
            for chunk in rag_chunks
        ]
        # Always include the knowledge base books as sources
        if not sources:
            sources = [
                {"title": "M. Laxmikanth - Indian Polity", "chapter": None, "page_start": None},
                {"title": "NCERT Textbooks (Classes 6-12)", "chapter": None, "page_start": None},
            ]

        return {
            "answer": response.content,
            "sources": sources,
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

        # 2. Attempt RAG retrieval (optional enhancement)
        rag_chunks = []
        try:
            logger.info("polity_generate_mcqs_retrieval_start user_id=%s topic=%s limit=5", user_id, topic)
            retrieval_response = await self._retrieval_service.retrieve(
                query=f"MCQs on {topic}",
                subject="Polity",
                limit=5,
            )
            rag_chunks = retrieval_response.chunks
            logger.info(
                "polity_generate_mcqs_retrieval_complete user_id=%s topic=%s chunk_count=%s",
                user_id,
                topic,
                len(rag_chunks),
            )
        except Exception:
            logger.warning("polity_generate_mcqs_retrieval_skipped user_id=%s topic=%s reason=retrieval_failed", user_id, topic)

        # 3. Build Prompt (knowledge-base-aware)
        rag_section = ""
        if rag_chunks:
            rag_section = (
                "\n\nADDITIONAL SOURCE MATERIAL FROM RAG:\n"
                + "\n\n".join([c.content for c in rag_chunks])
            )

        system_prompt = (
            "You are the Polity Examiner at AI University. Your goal is to generate high-quality "
            "multiple-choice questions for the UPSC Civil Services Examination.\n\n"
            f"{self.KNOWLEDGE_BASE}\n\n"
            f"TOPIC: {topic}\n"
            f"{rag_section}\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Generate {count} MCQs strictly based on the above knowledge base sources.\n"
            "2. Questions must be analytical and UPSC Prelims/Mains standard.\n"
            "3. Provide 4 distinct options for each question.\n"
            "4. Provide a clear explanation citing the specific source book and chapter for the correct answer.\n"
            "5. Include a mix of factual, conceptual, and application-based questions.\n"
            "6. Focus on constitutional provisions, amendments, landmark cases, and institutional mechanisms."
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
            f"{self.KNOWLEDGE_BASE}\n\n"
            f"STUDENT PERFORMANCE:\n"
            f"- Topic: {topic}\n"
            f"- Score: {score}/{total}\n"
            f"- Identified Weak Areas: {', '.join(weak_topics) if weak_topics else 'None'}\n\n"
            "Provide feedback grounded in the above knowledge base. Suggest specific chapters "
            "from Laxmikanth or NCERT books the student should revisit."
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

    def _build_teaching_system_prompt(self, context: Any, chunks: list[Any], current_topic_name: str | None = None) -> str:
        # Context summary
        progress_info = "New topic for the user."
        if context.progress:
            progress_info = (
                f"User has {context.progress.completion_percent}% completion "
                f"and {context.progress.confidence_score}/10 confidence."
            )
        
        weak_areas = ", ".join(context.weak_topics) if context.weak_topics else "None identified yet."
        
        # Optional RAG-enriched source chunks
        rag_section = ""
        if chunks:
            sources_text = "\n\n".join([
                f"SOURCE CHUNK (Chapter: {c.chapter}, Page: {c.page_start}):\n{c.content}"
                for c in chunks
            ])
            rag_section = f"\n\nADDITIONAL RETRIEVED SOURCE MATERIAL:\n{sources_text}"

        topic_context = f"\nCURRENT SYLLABUS TOPIC: {current_topic_name}\n" if current_topic_name else ""

        return (
            "You are the Polity Expert at AI University. Your goal is to teach Indian Polity "
            "for the UPSC Civil Services Examination. Use a professional, clear, and analytical tone.\n\n"
            f"{self.KNOWLEDGE_BASE}\n\n"
            f"USER CONTEXT:\n- {progress_info}\n- Weak Areas: {weak_areas}\n"
            f"{topic_context}"
            f"{rag_section}\n\n"
            "INSTRUCTIONS & SCIENTIFIC LEARNING METHODS:\n"
            "1. Ground your answer strictly in the knowledge base sources listed above.\n"
            "2. Always cite the specific book and chapter (e.g., 'As per Laxmikanth, Chapter 3...').\n"
            "3. Chunking: Break complex topics into small, digestible chunks. Do not output a massive wall of text.\n"
            "4. Active Recall: At the end of your explanation, provide 2-3 quick 'Active Recall' questions to test the user's immediate understanding.\n"
            "5. If the user has weak areas, try to clarify those points if relevant.\n"
            "6. Use UPSC-style analysis (importance, constitutional provisions, articles, amendments, implications).\n"
            "7. Structure your response with clear headings, bullet points, and constitutional references."
        )



