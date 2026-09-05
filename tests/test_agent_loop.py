"""
Unit Tests for Lab 1: Agent vs Chatbot Planning Loop, Draft Generation & Revisions
"""

import pytest
from app.agent.planner import MeetingOrganizerAgent
from app.agent.llm import parse_participants_input
from app.models.schemas import MeetingPlan, AgentPhase


def test_goal_predicate_and_phase_initialization():
    agent = MeetingOrganizerAgent()
    assert agent.satisfied() is False
    assert agent.is_draft_ready() is False
    assert agent.phase == AgentPhase.CLARIFICATION
    assert agent.goal["draft_generated"] is False
    assert agent.goal["is_approved"] is False
    assert agent.goal["plan_generated"] is False


def test_extraction_from_full_text():
    agent = MeetingOrganizerAgent()
    prompt = "Schedule a 45m architecture review with Alice and Bob on 2026-09-07"
    extracted = agent.extract_from_text(prompt)

    assert extracted["duration_minutes"] == 45
    assert extracted["topic"] == "Architecture Review"
    assert "Alice" in extracted["participants"]
    assert "Bob" in extracted["participants"]
    assert extracted["date_window"] == "2026-09-07"


def test_extraction_from_vague_request_and_clarification_questions():
    agent = MeetingOrganizerAgent()
    vague_prompt = "Let's meet"
    agent.extract_from_text(vague_prompt)

    questions = agent.get_missing_clarification_questions()
    # Must ask at least two clarification questions for vague requests
    assert len(questions) >= 2

    # Planning cycle pauses on missing requirement in CLARIFICATION phase
    plan = agent.run()
    assert plan is None
    assert agent.phase == AgentPhase.CLARIFICATION
    assert agent.satisfied() is False
    assert len(agent.log) == 1
    assert agent.log[0]["stopped"] is True
    assert "awaiting clarification" in agent.log[0]["stop_reason"]


def test_complete_draft_planning_cycle_and_approval():
    agent = MeetingOrganizerAgent()
    agent.extract_from_text("Schedule a design sync with Alice and Bob on Monday for 30 mins")

    # Step 1: Draft Plan Generation (Lab 1)
    draft_plan = agent.run()
    assert draft_plan is not None
    assert isinstance(draft_plan, MeetingPlan)
    assert agent.phase == AgentPhase.WAITING_FOR_APPROVAL
    assert agent.is_draft_ready() is True
    assert agent.satisfied() is False  # Not satisfied yet until user approves
    assert "PENDING_VERIFICATION" in draft_plan.time_slot
    assert draft_plan.duration_minutes == 30
    assert draft_plan.date == "Monday"
    assert "Alice" in draft_plan.participants
    assert "Bob" in draft_plan.participants
    assert len(draft_plan.agenda) >= 3
    assert len(draft_plan.minutes_outline.action_items) >= 2

    # Step 2: User Approval Gate -> Lab 2 Tool Execution -> Slot Selection
    plan_after_tools = agent.approve_draft()
    assert plan_after_tools is draft_plan
    assert agent.phase == AgentPhase.SLOT_SELECTION
    assert agent.satisfied() is False  # Not satisfied until user selects a slot
    assert len(plan_after_tools.verified_candidate_slots) > 0
    assert plan_after_tools.status == "awaiting_slot_selection"

    final_plan = agent.select_time_slot(1)
    assert final_plan is draft_plan
    assert agent.phase == AgentPhase.COMPLETED
    assert agent.satisfied() is True
    assert final_plan.status == "confirmed"
    assert final_plan.time_slot != "PENDING_VERIFICATION"
    assert final_plan.time_slot in plan_after_tools.verified_candidate_slots


def test_revision_mutates_existing_plan_in_place_with_history():
    agent = MeetingOrganizerAgent()
    agent.extract_from_text("Schedule a 45m sprint sync with Alice and Bob on 2026-09-07")
    draft_plan = agent.run()
    assert draft_plan is not None

    initial_meeting_id = draft_plan.meeting_id
    initial_plan_ref = agent.plan

    # Revise plan with user feedback
    revised = agent.revise("Make the duration 30 minutes, change date to Tuesday, and add security review to the agenda")

    # MUST be the same object mutated in place (not regenerated from scratch)
    assert revised is initial_plan_ref
    assert revised.meeting_id == initial_meeting_id
    assert revised.duration_minutes == 30
    assert revised.date == "Tuesday"
    assert revised.revision_count == 1
    assert len(revised.revision_history) == 1
    assert any("Security" in item.title for item in revised.agenda)

    # Check iteration log entries for revision
    last_two_entries = agent.log[-2:]
    assert last_two_entries[0]["planned"] == "apply user feedback to existing plan"
    assert last_two_entries[1]["planned"] == "confirm revised draft plan"
    assert "mutated existing plan in-place" in last_two_entries[1]["action"]
    assert last_two_entries[1]["stop_reason"] == "revision applied without restarting the loop"


def test_two_rounds_of_feedback_mutating_same_object():
    agent = MeetingOrganizerAgent()
    agent.extract_from_text("Schedule a 30m sync with Alice and Bob on 2026-09-07")
    agent.run()

    plan_ref = agent.plan

    # Round 1
    agent.revise("Make duration 45 mins")
    assert agent.plan.revision_count == 1
    assert agent.plan.duration_minutes == 45
    assert agent.plan is plan_ref

    # Round 2
    agent.revise("Add Charlie to participants list")
    assert agent.plan.revision_count == 2
    assert "Charlie" in agent.plan.participants
    assert agent.plan is plan_ref
    assert len(agent.plan.revision_history) == 2


def test_draft_plan_requires_explicit_approval_and_has_no_remote_assumption():
    agent = MeetingOrganizerAgent()
    agent.extract_from_text("Schedule a 30m design sync with Alice and Bob on Monday")
    draft = agent.run()

    assert draft is not None
    assert agent.goal["is_approved"] is False
    assert len(agent.executor.get_trace()) == 0
    assert all("Remote meeting" not in assumption for assumption in draft.assumptions)
    assert "PENDING_VERIFICATION" in draft.time_slot


def test_incomplete_request_asks_only_for_missing_topic():
    """Duration expressions must not be treated as topic; only topic should be missing."""
    agent = MeetingOrganizerAgent()
    result = agent.extract_from_text(
        "Schedule a meeting with Alice and Dana next Friday for 20 mins"
    )

    assert result["participants"] == ["Alice", "Dana"]
    assert result["duration_minutes"] == 20
    assert result["date_window"] == "Next Friday"
    assert result["topic"] is None
    assert result["missing_fields"] == ["topic"]
    assert result["clarification_questions"] == ["What would you like to discuss in this meeting?"]


def test_complete_request_skips_clarification():
    agent = MeetingOrganizerAgent()
    result = agent.extract_from_text(
        "Schedule a 45m architecture review with Alice and Bob on 2026-09-07"
    )
    assert result["missing_fields"] == []
    draft = agent.run()
    assert draft is not None
    assert agent.phase == AgentPhase.WAITING_FOR_APPROVAL


def test_lab2_runs_only_after_explicit_approval():
    agent = MeetingOrganizerAgent()
    agent.extract_from_text("Schedule a 30m design sync with Alice and Bob on Monday")
    agent.run()

    assert len(agent.executor.get_trace()) == 0
    agent.approve_draft()
    assert len(agent.executor.get_trace()) > 0


def test_slot_selection_required_before_confirmation():
    agent = MeetingOrganizerAgent()
    agent.extract_from_text("Schedule a design sync with Alice and Bob on Monday for 30 mins")
    draft = agent.run()
    meeting_id = draft.meeting_id

    agent.approve_draft()
    assert agent.plan.status == "awaiting_slot_selection"
    assert agent.plan.meeting_id == meeting_id

    agent.select_time_slot(1)
    assert agent.plan.status == "confirmed"
    assert agent.plan.meeting_id == meeting_id
    assert agent.satisfied() is True


def test_duration_revision_recalculates_agenda_durations():
    agent = MeetingOrganizerAgent()
    agent.extract_from_text("Schedule a 30m design sync with Alice and Bob on Monday")
    draft = agent.run()
    meeting_id = draft.meeting_id

    assert draft.duration_minutes == 30
    assert sum(item.duration_minutes for item in draft.agenda) == 30
    assert draft.agenda[0].duration_minutes == 6
    assert draft.agenda[1].duration_minutes == 18
    assert draft.agenda[2].duration_minutes == 6

    revised = agent.revise("Change the duration to 60 mins")
    assert revised is draft
    assert revised.meeting_id == meeting_id
    assert revised.duration_minutes == 60
    assert sum(item.duration_minutes for item in revised.agenda) == 60
    assert revised.agenda[0].duration_minutes == 10
    assert revised.agenda[1].duration_minutes == 40
    assert revised.agenda[2].duration_minutes == 10


def test_dynamic_clarification_questions_match_missing_fields_only():
    """Clarification questions must correspond only to genuinely missing goal fields."""
    cases = [
        (
            "schedule a meeting to discuss project planning next Tuesday for 10 mins",
            ["participants"],
            ["Who should attend this meeting?"],
            "Project Planning",
        ),
        (
            "Schedule a meeting with Alice and Bob next Tuesday for 10 mins",
            ["topic"],
            ["What would you like to discuss in this meeting?"],
            None,
        ),
        (
            "Schedule a meeting with Alice and Bob to discuss project planning",
            ["duration_minutes", "date_window"],
            [
                "How long should this meeting be (in minutes)?",
                "When would you like to schedule this (date or day)?",
            ],
            "Project Planning",
        ),
    ]
    for text, expected_missing, expected_questions, expected_topic in cases:
        agent = MeetingOrganizerAgent()
        result = agent.extract_from_text(text)
        assert result["missing_fields"] == expected_missing
        assert result["clarification_questions"] == expected_questions
        if expected_topic:
            assert agent.goal["topic"] == expected_topic


def test_parse_participants_input_from_clarification():
    assert parse_participants_input("alice and bob") == ["Alice", "Bob"]
    assert parse_participants_input("Alice, Bob and Charlie") == ["Alice", "Bob", "Charlie"]
    assert parse_participants_input("Alice, Bob, Charlie and Dana") == ["Alice", "Bob", "Charlie", "Dana"]


def test_apply_clarification_parses_participant_list():
    agent = MeetingOrganizerAgent()
    agent.extract_from_text("schedule a meeting to discuss project planning next Tuesday for 10 mins")
    agent.apply_clarification({"participants": "alice and bob"})
    assert agent.goal["participants"] == ["Alice", "Bob"]


def test_invalid_slot_choice_is_rejected():
    agent = MeetingOrganizerAgent()
    agent.extract_from_text("Schedule a design sync with Alice and Bob on Monday for 30 mins")
    agent.run()
    agent.approve_draft()

    with pytest.raises(ValueError, match="Invalid slot choice"):
        agent.select_time_slot(99)
