from __future__ import annotations

from typing import Any
from uuid import UUID

from app.memory.contracts import MemoryService


class LearningService:
    def __init__(self, memory_service: MemoryService) -> None:
        self._memory_service = memory_service

    async def get_user_dashboard(self, user_id: UUID) -> dict[str, Any]:
        """Provides a summary of user progress and due tasks."""
        # 1. Get all progress
        progress_list = await self._memory_service.list_progress(user_id)
        
        # 2. Get due revisions
        revisions = await self._memory_service.list_due_revisions(user_id)
        
        # 3. Get all Polity topics (hardcoded subject for MVP)
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

        return {
            "user_id": user_id,
            "progress": formatted_progress,
            "due_revisions": formatted_revisions,
            "available_subjects": [
                {
                    "code": "polity",
                    "name": "Indian Polity",
                    "topics_count": len(topics)
                }
            ]
        }
