"""
Compliance & Rubric Verification Tests for Lab 1 & Lab 2
Directly validates every instructor check and acceptance criterion in the Lab Guide.
"""

import pytest
from app.agent.planner import MeetingOrganizerAgent
from app.models.schemas import AgentPhase
from app.tools.executor import ToolExecutor, TOOLS
from app.data.mock_data import MOCK_CALENDARS_DB


def test_rubric_lab1_goal_as_data_predicate():
    """Instructor Check: Goal modeled as data -- a checkable predicate, not prose."""
    agent = MeetingOrganizerAgent()
    assert isinstance(agent.goal, dict)
    assert "draft_generated" in agent.goal
    assert "plan_generated" in agent.goal
    assert agent.satisfied() is False
    assert agent.is_draft_ready() is False

    agent.goal["draft_generated"] = True
    agent.phase = AgentPhase.WAITING_FOR_APPROVAL
    assert agent.is_draft_ready() is True


def test_rubric_lab1_asks_only_genuinely_missing_info():
    """Instructor Check: Planner next_step asks only for whatever goal field is still None."""
    agent = MeetingOrganizerAgent()
    agent.goal["topic"] = "Sprint Review"
    agent.goal["participants"] = ["Alice", "Bob"]
    # Missing: duration_minutes and date_window

    step, arg = agent.next_step()
    assert step == "ask"
    assert arg == "duration_minutes"

    agent.goal["duration_minutes"] = 45
    step, arg = agent.next_step()
    assert step == "ask"
    assert arg == "date_window"

    agent.goal["date_window"] = "2026-09-07"
    step, arg = agent.next_step()
    assert step == "generate_draft"


def test_rubric_lab1_mutation_without_scratch_regeneration():
    """
    Instructor Check: revise() mutates the existing self.plan object on feedback
    rather than calling run() again from scratch.
    """
    agent = MeetingOrganizerAgent()
    agent.extract_from_text("Schedule a 30m meeting with Alice and Bob on Monday for Project Sync")
    draft_plan = agent.run()
    assert draft_plan is not None

    orig_id = id(agent.plan)
    revised_plan = agent.revise("Make duration 45 mins and add security review to the agenda")
    
    # Must be the exact same Python object memory address
    assert id(revised_plan) == orig_id
    assert id(agent.plan) == orig_id
    assert agent.plan.duration_minutes == 45
    assert len(agent.plan.revision_history) == 1

    # Iteration log check
    log_actions = [entry["action"] for entry in agent.log]
    assert any("mutated existing plan in-place (not regenerated from scratch)" in a for a in log_actions)
    assert any(entry.get("stop_reason") == "revision applied without restarting the loop" for entry in agent.log)


def test_rubric_lab2_approval_gate_before_tool_execution():
    """
    Instructor Check: Agent does NOT execute tools or assume slots during Lab 1 draft phase.
    Tools run only after explicit user approval.
    """
    agent = MeetingOrganizerAgent()
    agent.extract_from_text("Schedule a 30m meeting with Alice and Bob on 2026-09-07 for Tech Sync")
    draft_plan = agent.run()

    # Zero tool calls executed before approval
    assert len(agent.executor.get_trace()) == 0
    assert "PENDING_VERIFICATION" in draft_plan.time_slot

    # Approve -> triggers Lab 2 tools
    final_plan = agent.approve_draft()
    assert len(agent.executor.get_trace()) >= 3
    assert final_plan.time_slot != "PENDING_VERIFICATION"


def test_rubric_lab2_structured_contracts_and_choke_point():
    """
    Instructor Check: Are inputs structured? Are tool results used correctly?
    Centralized choke point captures tool name, reason, inputs, outputs, success status, and errors.
    """
    agent = MeetingOrganizerAgent()
    agent.extract_from_text("Schedule a 30m meeting with Alice and Bob on 2026-09-07 for Tech Sync")
    agent.run()
    agent.approve_draft()

    trace = agent.executor.get_trace()
    assert len(trace) >= 3

    for entry in trace:
        assert "tool" in entry
        assert "reason" in entry
        assert "input" in entry
        assert "output" in entry
        assert "success" in entry
        assert isinstance(entry["input"], dict)
        assert isinstance(entry["output"], dict)
        assert len(entry["reason"]) > 0


def test_rubric_lab2_no_fabricated_information():
    """
    Instructor Check: Agent must use tool results when proposing meeting slots.
    Must never invent participant availability or valid meeting times.
    """
    agent = MeetingOrganizerAgent()
    # On 2026-09-07, Alice is busy 09:00-10:00 and 13:00-14:00; Bob is busy 11:00-12:30 and 15:00-16:00
    agent.extract_from_text("Schedule a 60m sync with Alice and Bob on 2026-09-07")
    agent.run()
    plan = agent.approve_draft()

    proposed_slot = plan.time_slot  # Should be e.g. 10:00-11:00, 14:00-15:00, or 16:00-17:00
    start_time, end_time = proposed_slot.split("-")

    # Verify no overlap with Alice's busy times
    for busy in MOCK_CALENDARS_DB["Alice"]["2026-09-07"]:
        assert not (max(start_time, busy["start"]) < min(end_time, busy["end"])), \
            f"Fabricated / Clashing slot! {proposed_slot} clashes with Alice {busy}"

    # Verify no overlap with Bob's busy times
    for busy in MOCK_CALENDARS_DB["Bob"]["2026-09-07"]:
        assert not (max(start_time, busy["start"]) < min(end_time, busy["end"])), \
            f"Fabricated / Clashing slot! {proposed_slot} clashes with Bob {busy}"
