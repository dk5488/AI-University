from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.memory.contracts import MemoryService, SemanticObservation
from app.rag.retrieval import RetrievalService


class PolityAgent:
    def __init__(
        self,
        memory_service: MemoryService,
        retrieval_service: RetrievalService,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
    ) -> None:
        self._memory_service = memory_service
        self._retrieval_service = retrieval_service
        self._llm = ChatOpenAI(model=model, api_key=api_key)

    async def teach(
        self,
        user_id: UUID,
        topic: str,
        message: str | None = None,
    ) -> dict[str, Any]:
        # 1. Get learning context
        topic_slug = topic.lower().replace(" ", "-")
        context = await self._memory_service.get_learning_context(
            user_id=user_id,
            subject_code="polity",
            topic_slug=topic_slug,
        )

        # 2. Retrieve source material
        retrieval_response = await self._retrieval_service.retrieve(
            query=topic,
            subject="Polity",
            limit=3,
        )

        # 3. Build Prompt
        system_prompt = self._build_teaching_system_prompt(context, retrieval_response.chunks)
        user_message = message or f"Teach me about {topic}."

        # 4. Generate Answer
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        
        response = await self._llm.ainvoke(messages)

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
        }

    def _build_teaching_system_prompt(self, context: Any, chunks: list[Any]) -> str:
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
