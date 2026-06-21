from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.agents.polity_agent import PolityAgent
from app.application.revision_service import RevisionService
from app.domain.learning import Assessment, AssessmentType
from app.domain.mcqs import MCQ, MCQOption, Quiz
from app.memory.contracts import MemoryService

logger = logging.getLogger(__name__)


class QuizService:
    def __init__(
        self,
        memory_service: MemoryService,
        polity_agent: PolityAgent,
        revision_service: RevisionService | None = None,
    ) -> None:
        self._memory_service = memory_service
        self._polity_agent = polity_agent
        self._revision_service = revision_service or RevisionService(memory_service)

    async def generate_quiz(
        self,
        user_id: UUID,
        subject_code: str,
        topic_slug: str,
        count: int = 5,
    ) -> dict[str, Any]:
        start_time = time.perf_counter()
        logger.info(
            "quiz_generate_start user_id=%s subject_code=%s topic_slug=%s count=%s",
            user_id,
            subject_code,
            topic_slug,
            count,
        )

        # 1. Resolve topic
        topic = await self._memory_service.get_topic_by_slug(subject_code, topic_slug)
        if not topic:
            logger.warning(
                "quiz_topic_not_found user_id=%s subject_code=%s topic_slug=%s",
                user_id,
                subject_code,
                topic_slug,
            )
            raise ValueError(f"Topic {topic_slug} not found for subject {subject_code}")
        logger.info("quiz_topic_resolved user_id=%s topic_id=%s topic_name=%s", user_id, topic.id, topic.name)

        # 2. Generate MCQs using agent
        if subject_code == "polity":
            try:
                quiz_schema = await self._polity_agent.generate_mcqs(
                    user_id=user_id,
                    topic=topic.name,
                    count=count,
                )
            except Exception:
                logger.exception("quiz_agent_failed user_id=%s topic=%s count=%s", user_id, topic.name, count)
                raise
        else:
            logger.warning("quiz_subject_unsupported user_id=%s subject_code=%s", user_id, subject_code)
            raise ValueError(f"Subject {subject_code} not supported yet")
        logger.info("quiz_agent_complete user_id=%s generated_questions=%s", user_id, len(quiz_schema.questions))

        # 3. Create Quiz domain model
        questions = []
        for q in quiz_schema.questions:
            options = tuple(
                MCQOption(content=opt, is_correct=(opt == q.correct_option))
                for opt in q.options
            )
            questions.append(
                MCQ(
                    stem=q.stem,
                    options=options,
                    explanation=q.explanation,
                )
            )
        
        quiz = Quiz(topic_id=topic.id, questions=tuple(questions))

        # 4. Store Quiz in session memory for evaluation later
        assessment_id = uuid4()
        await self._memory_service.set_session(
            user_id=user_id,
            session_id=f"quiz:{assessment_id}",
            value={
                "quiz_id": str(quiz.id),
                "topic_id": str(topic.id),
                "topic_name": topic.name,
                "questions": [
                    {
                        "id": str(q.id),
                        "stem": q.stem,
                        "options": [opt.content for opt in q.options],
                        "correct_option": next(opt.content for opt in q.options if opt.is_correct),
                        "explanation": q.explanation,
                    }
                    for q in quiz.questions
                ],
            },
            ttl_seconds=3600,
        )
        logger.info("quiz_session_saved user_id=%s assessment_id=%s ttl_seconds=3600", user_id, assessment_id)

        # 5. Return quiz to user (WITHOUT correct options or explanations)
        logger.info(
            "quiz_generate_complete user_id=%s assessment_id=%s question_count=%s duration_ms=%.2f",
            user_id,
            assessment_id,
            len(quiz.questions),
            (time.perf_counter() - start_time) * 1000,
        )
        return {
            "assessment_id": assessment_id,
            "questions": [
                {
                    "id": q.id,
                    "stem": q.stem,
                    "options": [opt.content for opt in q.options],
                }
                for q in quiz.questions
            ],
        }

    async def submit_quiz(
        self,
        user_id: UUID,
        assessment_id: UUID,
        answers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        start_time = time.perf_counter()
        logger.info(
            "quiz_submit_start user_id=%s assessment_id=%s answer_count=%s",
            user_id,
            assessment_id,
            len(answers),
        )

        # 1. Retrieve quiz from session
        session_data = await self._memory_service.get_session(user_id, f"quiz:{assessment_id}")
        if not session_data:
            logger.warning("quiz_session_missing user_id=%s assessment_id=%s", user_id, assessment_id)
            raise ValueError("Quiz not found or expired")
        logger.info("quiz_session_loaded user_id=%s assessment_id=%s", user_id, assessment_id)

        # 2. Score
        score = 0
        total = len(session_data["questions"])
        results = []
        weak_topics = []

        answer_map = {UUID(a["question_id"]): a["selected_option"] for a in answers}

        for q in session_data["questions"]:
            q_id = UUID(q["id"])
            user_opt = answer_map.get(q_id)
            correct_opt = q["correct_option"]
            is_correct = (user_opt == correct_opt)
            
            if is_correct:
                score += 1
            else:
                weak_topics.append(session_data["topic_name"])

            results.append({
                "question_id": q_id,
                "is_correct": is_correct,
                "correct_option": correct_opt,
                "user_option": user_opt,
                "explanation": q["explanation"],
            })

        weak_topics = list(set(weak_topics))

        # 3. Get personalized feedback from agent
        feedback = await self._polity_agent.evaluate_mcq_submission(
            user_id=user_id,
            topic=session_data["topic_name"],
            score=score,
            total=total,
            weak_topics=weak_topics,
        )

        # 4. Persist Assessment
        assessment = Assessment(
            user_id=user_id,
            topic_id=UUID(session_data["topic_id"]),
            assessment_type=AssessmentType.MCQ,
            score=score,
            total=total,
            submitted_at=datetime.now(timezone.utc),
            weak_topics=tuple(weak_topics),
            id=assessment_id,
        )
        await self._memory_service.record_assessment(assessment)

        # 5. Plan Revisions if needed
        await self._revision_service.plan_revisions_for_assessment(assessment)
        logger.info(
            "quiz_revision_planned user_id=%s assessment_id=%s weak_topic_count=%s",
            user_id,
            assessment_id,
            len(weak_topics),
        )

        # 6. Clear session
        await self._memory_service.clear_session(user_id, f"quiz:{assessment_id}")
        logger.info(
            "quiz_submit_complete user_id=%s assessment_id=%s score=%s total=%s duration_ms=%.2f",
            user_id,
            assessment_id,
            score,
            total,
            (time.perf_counter() - start_time) * 1000,
        )

        return {
            "score": score,
            "total": total,
            "percentage": assessment.percentage,
            "feedback": feedback,
            "results": results,
            "weak_topics": weak_topics,
        }
