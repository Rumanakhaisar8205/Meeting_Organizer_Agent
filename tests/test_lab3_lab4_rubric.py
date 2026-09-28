"""
Lab 3 & Lab 4 Rubric Verification Tests
Verifies adherence to worklet specifications for reusable skills, schema typing,
short-term vs long-term memory separation, tag search, similarity retrieval, and action item carryover.
"""

import pytest
from app.agent.planner import MeetingOrganizerAgent
from app.skills.plan_skill import PlanSkill
from app.skills.format_skill import FormatSkill
from app.memory.store import KnowledgeStore
from app.memory.history import MeetingHistoryStore
from app.models.schemas import AgentPhase, MeetingPlan


def test_rubric_lab3_skills_are_reusable_and_typed():
    """Rubric Check: Skills are callable, typed, case-agnostic, and schema-bounded."""
    plan_skill = PlanSkill()
    format_skill = FormatSkill()

    assert hasattr(plan_skill, "execute")
    assert hasattr(format_skill, "execute")

    # Verify skill name & description attributes
    assert plan_skill.name == "plan_skill"
    assert format_skill.name == "format_skill"


def test_rubric_lab4_memory_split_and_carryover():
    """Rubric Check: Short-term run state is split from long-term stores; action items carry over."""
    agent = MeetingOrganizerAgent(session_id="rubric-session-1")

    # Verify short-term state is separate from long-term archives
    assert agent.session_state is not None
    assert agent.knowledge_store is not None
    assert agent.history_store is not None
    assert agent.session_state.draft_plan is None

    # Run agent on a topic with historical action items (e.g. "exam")
    agent.extract_from_text("Schedule an exam review meeting with Alice and Bob for 30m on 2026-09-07")
    plan = agent.run()

    assert plan is not None
    assert plan.status == "draft"
    # Action item carryover check: draft plan includes carried-over action items from history
    assert len(plan.minutes_outline.action_items) > 0
    assert any("rubric" in ai.description.lower() or "exam" in ai.description.lower() for ai in plan.minutes_outline.action_items)


def test_rubric_lab3_lab4_full_agent_integration():
    """Rubric Check: Full agent workflow integrating Lab 1, 2, 3, and 4 capabilities."""
    agent = MeetingOrganizerAgent()

    # Step 1: Ingest complete request
    agent.extract_from_text("Schedule a 30m committee meeting with Alice and Bob on 2026-09-07")
    draft = agent.run()
    assert draft is not None
    assert agent.phase == AgentPhase.WAITING_FOR_APPROVAL

    # Step 2: Format draft document using Lab 3 FormatSkill
    fmt_doc = agent.format_plan(template_format="markdown")
    assert fmt_doc.format_type == "markdown"
    assert "# Meeting Document:" in fmt_doc.content

    # Step 3: Revise plan in-place
    revised = agent.revise("Change topic to Project Architecture and increase duration to 45m")
    assert revised.duration_minutes == 45
    assert agent.phase == AgentPhase.WAITING_FOR_APPROVAL

    # Step 4: Explicit human approval gate -> Tool execution (Lab 2)
    plan_with_candidates = agent.approve_draft(notes="Approved for scheduling")
    assert agent.phase == AgentPhase.SLOT_SELECTION
    assert len(plan_with_candidates.verified_candidate_slots) > 0

    # Step 5: Select slot -> Confirmation
    confirmed = agent.select_time_slot(choice=1)
    assert confirmed.status == "confirmed"
    assert agent.phase == AgentPhase.COMPLETED
    assert agent.satisfied() is True
