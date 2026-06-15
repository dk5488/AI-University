from __future__ import annotations

from typing import Any
from uuid import UUID

from app.domain.learning import Assessment, RevisionTask
from app.domain.revision_policy import SpacedRevisionPolicy
from app.memory.contracts import MemoryService


class RevisionService:
    def __init__(
        self,
        memory_service: MemoryService,
        policy: SpacedRevisionPolicy | None = None,
    ) -> None:
        self._memory_service = memory_service
        self._policy = policy or SpacedRevisionPolicy()

    async def plan_revisions_for_assessment(self, assessment: Assessment) -> tuple[RevisionTask, ...]:
        """Plans and persists revision tasks for a given assessment."""
        tasks = self._policy.plan_revisions(assessment)
        if tasks:
            await self._memory_service.create_revision_tasks(tasks)
        return tasks

    async def get_due_revisions(self, user_id: UUID) -> tuple[dict[str, Any], ...]:
        """Retrieves due revision tasks for a user, enriched with topic names."""
        tasks = await self._memory_service.list_due_revisions(user_id)
        
        # In a real app, we'd join with topics table. 
        # Here we'll just return the tasks with IDs.
        results = []
        for task in tasks:
            results.append({
                "revision_task_id": task.id,
                "topic_id": task.topic_id,
                "due_at": task.due_at,
                "reason": task.reason,
                "status": task.status,
            })
        return tuple(results)
