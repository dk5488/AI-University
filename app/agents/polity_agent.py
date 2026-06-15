from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.memory.contracts import MemoryService, SemanticObservation
from app.rag.retrieval import RetrievalService


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
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
    ) -> None:
        self._memory_service = memory_service
        self._retrieval_service = retrieval_service
        self._llm = ChatOpenAI(model=model, api_key=api_key)
        self._quiz_llm = self._llm.with_structured_output(QuizSchema)

    async def teach(
        self,
        user_id: UUID,
        topic: str,
        message: str | None = None,
    ) -> dict[str, Any]:
        # ... (unchanged)
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

    async def generate_mcqs(
        self,
        user_id: UUID,
        topic: str,
        count: int = 5,
    ) -> QuizSchema:
        # ... (unchanged)
        # 1. Get context
        topic_slug = topic.lower().replace(" ", "-")
        context = await self._memory_service.get_learning_context(
            user_id=user_id,
            subject_code="polity",
            topic_slug=topic_slug,
        )

        # 2. Retrieve source material
        retrieval_response = await self._retrieval_service.retrieve(
            query=f"MCQs on {topic}",
            subject="Polity",
            limit=5,
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
        
        return await self._quiz_llm.ainvoke(messages)

    async def evaluate_mcq_submission(
        self,
        user_id: UUID,
        topic: str,
        score: int,
        total: int,
        weak_topics: list[str],
    ) -> str:
        """Generate personalized feedback for an MCQ attempt."""
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
        
        response = await self._llm.ainvoke(messages)
        return response.content

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
