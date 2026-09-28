"""
Lab 4: Memory & Retrieval - Short-Term Run State
Manages short-term execution memory (transient run state, candidate drafts, iteration logs).
Conflating run state with stored reference/archive is explicitly avoided.
"""

from typing import Dict, Any, List, Optional
from app.models.schemas import MeetingPlan, RevisionHistoryEntry, IterationLogEntry


class ShortTermSessionState:
    """
    Holds ephemeral execution state for an active meeting agent run session.
    Keeps transient draft states isolated from long-term memory archives.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.goal: Dict[str, Any] = {}
        self.draft_plan: Optional[MeetingPlan] = None
        self.candidate_history: List[MeetingPlan] = []
        self.revision_history: List[RevisionHistoryEntry] = []
        self.iteration_log: List[IterationLogEntry] = []

    def set_draft(self, plan: MeetingPlan) -> None:
        """Update active draft candidate and log in candidate history."""
        self.draft_plan = plan
        self.candidate_history.append(plan)

    def add_revision(self, entry: RevisionHistoryEntry) -> None:
        """Record a revision mutation in session history."""
        self.revision_history.append(entry)

    def add_iteration(self, entry: IterationLogEntry) -> None:
        """Record an iteration log entry."""
        self.iteration_log.append(entry)

    def get_latest_candidate(self) -> Optional[MeetingPlan]:
        """Return current active draft candidate."""
        return self.draft_plan

    def clear(self) -> None:
        """Reset short-term run state."""
        self.goal.clear()
        self.draft_plan = None
        self.candidate_history.clear()
        self.revision_history.clear()
        self.iteration_log.clear()
