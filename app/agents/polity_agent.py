import logging
import time
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from app.domain.curriculum import CurriculumNode, NodeStatus
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
            "max_retries": 3,
        }
        if api_key:
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
        conversation_history: list[dict[str, str]] | None = None,
        current_topic_context: str | None = None,
    ) -> dict[str, Any]:
        logger.info("polity_teach_start provider=gemini user_id=%s topic=%s message_length=%s", user_id, topic, len(message or ""))
        start_time = time.perf_counter()
        
        # 0. Handle Dynamic/Auto Topic Resolution
        resolved_topic = topic
        status_message = ""
        curriculum_context = await self._get_curriculum_context(user_id, topic)
        current_node = curriculum_context.get("node")
        if topic.lower() in ("auto", "next", "status"):
            current_node = curriculum_context.get("current_node")
            current_progress = curriculum_context.get("current_progress")
            if current_node:
                resolved_topic = current_node.title
                status = current_progress.status if current_progress else NodeStatus.NOT_STARTED
                if topic.lower() == "status":
                    status_message = f"You are currently on **{resolved_topic}** ({status}). "
                elif status == NodeStatus.NOT_STARTED:
                    status_message = f"Starting the next optimized syllabus item: **{resolved_topic}**. "
                # For IN_PROGRESS — no blocking message; let the LLM continue
                # naturally from conversation history
            else:
                current_topic, progress = await self._memory_service.get_current_topic(user_id, "polity")
                if current_topic:
                    resolved_topic = current_topic.name
                    pct = progress.completion_percent if progress else 0
                    status_message = f"Using your current topic: **{resolved_topic}** ({pct}% complete). "
                else:
                    resolved_topic = "Historical Background"  # fallback

        curriculum_context = await self._get_curriculum_context(user_id, resolved_topic)
        current_node = curriculum_context.get("node") or curriculum_context.get("current_node")
        await self._mark_curriculum_item_started(user_id, current_node)
        
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
        system_prompt = self._build_teaching_system_prompt(
            context,
            rag_chunks,
            current_topic_name=resolved_topic,
            curriculum_context=curriculum_context,
        )
        user_message = message or f"Teach me about {resolved_topic}."

        # 4. Generate Answer — include conversation history for context
        messages = [SystemMessage(content=system_prompt)]

        # Inject recent conversation history so the LLM remembers what it taught
        if conversation_history:
            for entry in conversation_history[-10:]:  # last 10 messages
                role = entry.get("role", "user")
                content = entry.get("content", "")
                if role == "assistant":
                    from langchain_core.messages import AIMessage
                    messages.append(AIMessage(content=content))
                else:
                    messages.append(HumanMessage(content=content))

        messages.append(HumanMessage(content=user_message))
        
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
                created_at=datetime.now(UTC),
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
            "answer": final_answer,
            "sources": sources,
            "topic": resolved_topic,
            "subject": "Polity",
            "next_actions": [
                f"Generate MCQs on {resolved_topic}",
                f"Explain {resolved_topic} in more detail",
                "Mark current item complete",
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

    async def _get_curriculum_context(self, user_id: UUID, topic: str) -> dict[str, Any]:
        try:
            nodes = await self._memory_service.get_curriculum("polity")
        except Exception:
            nodes = []
        if not isinstance(nodes, list):
            nodes = []

        try:
            position = await self._memory_service.get_current_curriculum_position(
                user_id,
                "polity",
            )
        except Exception:
            position = (None, None)
        if not isinstance(position, tuple) or len(position) != 2:
            position = (None, None)
        current_node, current_progress = position
        node = current_node if topic.lower() in ("auto", "next", "status") else self._find_node(nodes, topic)
        if node is None:
            node = current_node

        node_map = {item.id: item for item in nodes}
        child_map: dict[str | None, list[CurriculumNode]] = defaultdict(list)
        for item in nodes:
            child_map[item.parent_id].append(item)
        for children in child_map.values():
            children.sort(key=lambda item: item.learning_order)

        path: list[CurriculumNode] = []
        if node:
            cursor: CurriculumNode | None = node
            seen: set[str] = set()
            while cursor and cursor.id not in seen:
                seen.add(cursor.id)
                path.insert(0, cursor)
                cursor = node_map.get(cursor.parent_id) if cursor.parent_id else None

        prerequisite_titles = [
            node_map[item_id].title for item_id in node.prerequisites
            if node and item_id in node_map
        ] if node else []

        next_items: list[CurriculumNode] = []
        if node:
            leaf_nodes = sorted(
                [item for item in nodes if not item.child_ids],
                key=lambda item: item.learning_order,
            )
            for index, item in enumerate(leaf_nodes):
                if item.id == node.id:
                    next_items = leaf_nodes[index + 1 : index + 4]
                    break

        return {
            "node": node,
            "current_node": current_node,
            "current_progress": current_progress,
            "path": path,
            "prerequisite_titles": prerequisite_titles,
            "next_items": next_items,
        }

    def _find_node(self, nodes: list[CurriculumNode], topic: str) -> CurriculumNode | None:
        normalized_topic = topic.strip().lower()
        if not normalized_topic:
            return None
        for node in nodes:
            if node.id.lower() == normalized_topic or node.title.lower() == normalized_topic:
                return node
        for node in nodes:
            title = node.title.lower()
            if normalized_topic in title or title in normalized_topic:
                return node
        return None

    async def _mark_curriculum_item_started(
        self,
        user_id: UUID,
        node: CurriculumNode | None,
    ) -> None:
        if node is None or node.child_ids:
            return
        try:
            existing_progress = await self._memory_service.get_curriculum_progress(user_id, "polity")
        except Exception:
            existing_progress = []
        if not isinstance(existing_progress, list):
            existing_progress = []
        existing = next((item for item in existing_progress if item.node_id == node.id), None)
        if existing and existing.status != NodeStatus.NOT_STARTED:
            return
        await self._memory_service.upsert_curriculum_progress(
            user_id,
            node.id,
            NodeStatus.IN_PROGRESS,
            started_at=datetime.now(UTC),
        )

    def _build_teaching_system_prompt(
        self,
        context: Any,
        chunks: list[Any],
        current_topic_name: str | None = None,
        curriculum_context: dict[str, Any] | None = None,
    ) -> str:
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
        curriculum_section = self._format_curriculum_prompt_context(curriculum_context or {})

        return (
            "You are the Polity Expert at AI University. Your goal is to teach Indian Polity "
            "for the UPSC Civil Services Examination. Use a professional, clear, and analytical tone.\n\n"
            f"{self.KNOWLEDGE_BASE}\n\n"
            f"USER CONTEXT:\n- {progress_info}\n- Weak Areas: {weak_areas}\n"
            f"{topic_context}"
            f"{curriculum_section}"
            f"{rag_section}\n\n"
            "INSTRUCTIONS & SCIENTIFIC LEARNING METHODS:\n"
            "1. Ground your answer strictly in the knowledge base sources listed above.\n"
            "2. Always cite the specific book and chapter (e.g., 'As per Laxmikanth, Chapter 3...').\n"
            "3. Teach the current optimized syllabus item. If the user asks about a concept that was "
            "mentioned in your lesson (e.g., East India Company, Battle of Plassey, British Parliament), "
            "answer it in the context of Polity. These are NOT off-topic — they are part of the Polity syllabus.\n"
            "4. Minimize effort and maximize UPSC throughput: explain the smallest useful concept, its exam relevance, and the exact recall hooks.\n"
            "5. Chunking: Break complex topics into small, digestible chunks. Do not output a massive wall of text.\n"
            "6. Active Recall: At the end of your explanation, provide 2-3 quick 'Active Recall' questions to test the user's immediate understanding.\n"
            "7. If the user asks a doubt or follow-up, answer it directly first, then reconnect it to the current syllabus item. "
            "NEVER say you cannot answer a question about something you just taught.\n"
            "8. If the user says they didn't understand something, re-explain it differently using simpler language, analogies, or a different angle. "
            "Do NOT repeat the exact same explanation.\n"
            "9. If the user asks for more detail, go deeper into the concept. Do NOT re-teach from scratch.\n"
            "10. If the user has weak areas, try to clarify those points if relevant.\n"
            "11. Use UPSC-style analysis (importance, constitutional provisions, articles, amendments, implications).\n"
            "12. Structure your response with clear headings, bullet points, and constitutional references.\n"
            "13. You have conversation history available. Use it to avoid repeating what you already taught. "
            "Build on previous explanations rather than starting over."
        )

    def _format_curriculum_prompt_context(self, curriculum_context: dict[str, Any]) -> str:
        node = curriculum_context.get("node")
        if node is None:
            return ""

        path = " > ".join(item.title for item in curriculum_context.get("path", []))
        prerequisites = curriculum_context.get("prerequisite_titles") or []
        next_items = curriculum_context.get("next_items") or []
        progress = curriculum_context.get("current_progress")

        lines = [
            "\nOPTIMIZED CURRICULUM CONTEXT:",
            f"- Current node: {node.title} ({node.level})",
        ]
        if path:
            lines.append(f"- Breadcrumb path: {path}")
        if progress:
            lines.append(f"- User's current node status: {progress.status}")
        lines.append(
            "- Prerequisites already expected: "
            + (", ".join(prerequisites) if prerequisites else "None listed")
        )
        lines.append(
            "- Upcoming items: "
            + (", ".join(item.title for item in next_items) if next_items else "None listed")
        )
        return "\n".join(lines) + "\n"



