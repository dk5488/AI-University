from __future__ import annotations

from typing import Any
from uuid import UUID

from app.application.curriculum_service import CurriculumService
from app.memory.contracts import MemoryService


class LearningService:
    def __init__(
        self,
        memory_service: MemoryService,
        curriculum_service: CurriculumService | None = None,
    ) -> None:
        self._memory_service = memory_service
        self._curriculum_service = curriculum_service

    async def get_user_dashboard(self, user_id: UUID) -> dict[str, Any]:
        """Provides a summary of user progress and due tasks."""
        # 1. Get all progress
        progress_list = await self._memory_service.list_progress(user_id)
        
        # 2. Get due revisions
        revisions = await self._memory_service.list_due_revisions(user_id)
        
        # 3. Get all Polity topics
        topics = await self._memory_service.list_topics("polity")
        topic_map = {t.id: t for t in topics}

        # 4. Format progress
        formatted_progress = []
        for p in progress_list:
            topic = topic_map.get(p.topic_id)
            formatted_progress.append({
                "topic_name": topic.name if topic else "Unknown Topic",
                "topic_slug": topic.slug if topic else "unknown",
                "completion_percent": p.completion_percent,
                "confidence_score": p.confidence_score,
                "last_studied_at": p.last_studied_at,
            })

        # 5. Format revisions
        formatted_revisions = []
        for r in revisions:
            topic = topic_map.get(r.topic_id)
            formatted_revisions.append({
                "task_id": r.id,
                "topic_name": topic.name if topic else "Unknown Topic",
                "topic_slug": topic.slug if topic else "unknown",
                "due_at": r.due_at,
                "reason": r.reason,
            })

        # 6. Calculate studied topics count (only topics user has actually studied)
        studied_count = 0
        current_position_title = None

        if self._curriculum_service:
            studied_count = await self._curriculum_service.get_studied_topics_count(
                user_id, "polity",
            )
            # Get current curriculum position
            summary = await self._curriculum_service.get_user_progress_summary(
                user_id, "polity",
            )
            if summary.get("current_position"):
                current_position_title = summary["current_position"].get("title")
        else:
            # Fallback: count progress entries with completion > 0
            studied_count = sum(
                1 for p in progress_list
                if topic_map.get(p.topic_id) is not None and p.completion_percent > 0
            )

        return {
            "user_id": user_id,
            "progress": formatted_progress,
            "due_revisions": formatted_revisions,
            "available_subjects": [
                {
                    "code": "polity",
                    "name": "Indian Polity",
                    "topics_count": studied_count,
                    "current_position": current_position_title,
                }
            ],
        }
