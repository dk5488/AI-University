from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.domain.learning import Assessment, RevisionTask


class SpacedRevisionPolicy:
    """Implements the spaced repetition policy for learning."""

    def __init__(
        self,
        intervals: tuple[int, ...] = (1, 7, 30),
        weak_threshold: float = 60.0,
    ) -> None:
        self._intervals = intervals
        self._weak_threshold = weak_threshold

    def plan_revisions(self, assessment: Assessment) -> tuple[RevisionTask, ...]:
        """Plans revision tasks based on assessment performance."""
        if assessment.percentage >= self._weak_threshold:
            return ()

        tasks = []
        now = datetime.now(timezone.utc)
        
        for days in self._intervals:
            due_at = now + timedelta(days=days)
            tasks.append(
                RevisionTask(
                    user_id=assessment.user_id,
                    topic_id=assessment.topic_id,
                    due_at=due_at,
                    reason=f"Weak score ({assessment.score}/{assessment.total}) in {assessment.assessment_type}",
                    source_assessment_id=assessment.id,
                )
            )
            
        return tuple(tasks)
