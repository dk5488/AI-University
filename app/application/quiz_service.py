from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.agents.polity_agent import PolityAgent
from app.application.revision_service import RevisionService
from app.domain.learning import Assessment, AssessmentType
from app.domain.mcqs import MCQ, MCQOption, Quiz
from app.memory.contracts import MemoryService


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
        # 1. Resolve topic
        topic = await self._memory_service.get_topic_by_slug(subject_code, topic_slug)
        if not topic:
            raise ValueError(f"Topic {topic_slug} not found for subject {subject_code}")

        # 2. Generate MCQs using agent
        if subject_code == "polity":
            quiz_schema = await self._polity_agent.generate_mcqs(
                user_id=user_id,
                topic=topic.name,
                count=count,
            )
        else:
            raise ValueError(f"Subject {subject_code} not supported yet")

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

        # 5. Return quiz to user (WITHOUT correct options or explanations)
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
        # 1. Retrieve quiz from session
        session_data = await self._memory_service.get_session(user_id, f"quiz:{assessment_id}")
        if not session_data:
            raise ValueError("Quiz not found or expired")

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

        # 6. Clear session
        await self._memory_service.clear_session(user_id, f"quiz:{assessment_id}")

        return {
            "score": score,
            "total": total,
            "percentage": assessment.percentage,
            "feedback": feedback,
            "results": results,
            "weak_topics": weak_topics,
        }
