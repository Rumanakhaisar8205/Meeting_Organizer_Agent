"""
In-Memory Session Service
Manages meeting planning sessions, phase state persistence across turns,
approval gating, and trace logging.
"""

import uuid
from typing import Dict, Optional, Any
from app.agent.planner import MeetingOrganizerAgent
from app.models.schemas import (
    AgentPhase,
    SessionStateResponse,
    SessionTraceResponse,
    IterationLogEntry,
    ToolTraceEntry,
)


class MeetingSession:
    """Wrapper holding an agent instance and session metadata."""

    def __init__(self, session_id: str, agent: Optional[MeetingOrganizerAgent] = None):
        self.session_id = session_id
        self.agent = agent or MeetingOrganizerAgent()

    def to_state_response(self) -> SessionStateResponse:
        """Construct a clean API response representing the current session state."""
        missing = [
            f for f in ("topic", "participants", "duration_minutes", "date_window")
            if self.agent.goal.get(f) is None
        ]
        questions = self.agent.get_missing_clarification_questions() if missing else []
        
        status = self.agent.phase.value.lower()
        if self.agent.plan:
            if self.agent.phase == AgentPhase.WAITING_FOR_APPROVAL:
                status = "waiting_for_approval"
            elif self.agent.phase == AgentPhase.COMPLETED:
                status = "confirmed" if self.agent.plan.status == "confirmed" else "completed"
            elif self.agent.phase == AgentPhase.REVISION:
                status = "revised"

        return SessionStateResponse(
            session_id=self.session_id,
            current_phase=self.agent.phase,
            status=status,
            goal=self.agent.goal,
            missing_fields=missing,
            clarification_questions=questions,
            plan=self.agent.plan,
            revision_history=self.agent.plan.revision_history if self.agent.plan else [],
            iterations_count=len(self.agent.log),
            tool_calls_count=len(self.agent.executor.trace),
        )

    def to_trace_response(self) -> SessionTraceResponse:
        """Construct full iteration and tool trace audit logs."""
        iteration_entries = [IterationLogEntry(**entry) for entry in self.agent.log]
        tool_entries = [ToolTraceEntry(**entry) for entry in self.agent.executor.trace]
        return SessionTraceResponse(
            session_id=self.session_id,
            current_phase=self.agent.phase,
            iteration_log=iteration_entries,
            tool_trace=tool_entries,
        )


class SessionService:
    """In-memory registry of active meeting planning sessions."""

    def __init__(self):
        self._sessions: Dict[str, MeetingSession] = {}

    def create_session(self, request_text: Optional[str] = None) -> SessionStateResponse:
        """Create a new planning session and optionally run extraction & planning."""
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        session = MeetingSession(session_id=session_id)
        self._sessions[session_id] = session

        if request_text:
            session.agent.extract_from_text(request_text)
            session.agent.run()

        return session.to_state_response()

    def get_session(self, session_id: str) -> SessionStateResponse:
        """Retrieve the state of an existing session."""
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.to_state_response()

    def clarify_session(self, session_id: str, answers: Dict[str, Any]) -> SessionStateResponse:
        """Supply answers to missing goal parameters and resume the planning loop."""
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        session.agent.run(user_answers=answers)
        return session.to_state_response()

    def revise_session(self, session_id: str, feedback: str) -> SessionStateResponse:
        """Mutate the existing draft plan in-place based on user feedback."""
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        session.agent.revise(feedback)
        return session.to_state_response()

    def approve_session(self, session_id: str, notes: Optional[str] = None, approved: bool = True) -> SessionStateResponse:
        """Explicitly approve the draft plan before executing Lab 2 verification tools."""
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        if not approved:
            session.agent.goal["is_approved"] = False
            session.agent.phase = AgentPhase.WAITING_FOR_APPROVAL
            return session.to_state_response()
        session.agent.approve_draft(notes=notes)
        return session.to_state_response()

    def select_slot(self, session_id: str, choice: int) -> SessionStateResponse:
        """Apply the user's Top-K slot selection, confirming the existing MeetingPlan."""
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        session.agent.select_time_slot(choice)
        return session.to_state_response()

    def get_session_trace(self, session_id: str) -> SessionTraceResponse:
        """Retrieve the full iteration and tool trace logs for auditing."""
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.to_trace_response()

    def get_session_agent(self, session_id: str) -> MeetingOrganizerAgent:
        """Retrieve the MeetingOrganizerAgent instance of an active session."""
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found")
        return session.agent

    def clear_all(self) -> None:
        """Clear all stored sessions (useful for test isolation)."""
        self._sessions.clear()


# Global in-memory singleton
session_service = SessionService()