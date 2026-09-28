"""
Tests for Lab 3: Skill Creation (PlanSkill and FormatSkill)
Verifies typed inputs/outputs, schema validation, and multi-case reuse without code changes.
"""

import pytest
from app.skills.plan_skill import PlanSkill
from app.skills.format_skill import FormatSkill
from app.models.schemas import (
    PlanSkillInput,
    LockedPlanBlueprint,
    FormatSkillInput,
    FormattedDocumentResponse,
    ActionItemTemplate,
    MeetingPlan,
)


def test_plan_skill_execution():
    """Verify PlanSkill produces a locked blueprint across different meeting types."""
    skill = PlanSkill()

    # Case 1: Committee Meeting with prior action items
    input1 = PlanSkillInput(
        topic="Curriculum & Exam Review",
        duration_minutes=45,
        participants=["Faculty Advisor", "HoD", "Committee Member A"],
        date_window="2026-09-15",
        meeting_type="committee",
        prior_action_items=[
            ActionItemTemplate(description="Draft rubric", owner="Alice", deadline="2026-09-01")
        ],
    )
    blueprint1 = skill.execute(input1)

    assert isinstance(blueprint1, LockedPlanBlueprint)
    assert blueprint1.topic == "Curriculum & Exam Review"
    assert blueprint1.meeting_type == "committee"
    assert blueprint1.duration_minutes == 45
    assert blueprint1.constraints_locked is True
    assert len(blueprint1.agenda_structure) >= 3
    assert any("Action Items" in item.title for item in blueprint1.agenda_structure)

    # Case 2: Engineering Standup (different meeting type, zero code changes)
    input2 = PlanSkillInput(
        topic="Daily Engineering Standup",
        duration_minutes=15,
        participants=["Alice", "Bob", "Charlie"],
        date_window="2026-09-08",
        meeting_type="standup",
    )
    blueprint2 = skill.execute(input2)
    assert isinstance(blueprint2, LockedPlanBlueprint)
    assert blueprint2.meeting_type == "standup"
    assert blueprint2.duration_minutes == 15


def test_plan_skill_to_meeting_plan_conversion():
    """Verify converting LockedPlanBlueprint to standard MeetingPlan."""
    skill = PlanSkill()
    blueprint = skill.execute(
        PlanSkillInput(
            topic="Sprint Retrospective",
            duration_minutes=30,
            participants=["Alice", "Bob"],
            date_window="2026-09-10",
            meeting_type="sprint",
        )
    )
    plan = skill.to_meeting_plan(blueprint)
    assert isinstance(plan, MeetingPlan)
    assert plan.title == "Sprint Retrospective"
    assert plan.status == "draft"
    assert plan.time_slot == "PENDING_VERIFICATION"


def test_format_skill_markdown_text_html():
    """Verify FormatSkill renders Markdown, Text, and HTML outputs."""
    plan_skill = PlanSkill()
    format_skill = FormatSkill()

    blueprint = plan_skill.execute(
        PlanSkillInput(
            topic="Architecture Review",
            duration_minutes=60,
            participants=["Alice", "Bob"],
            date_window="2026-09-12",
        )
    )
    plan = plan_skill.to_meeting_plan(blueprint)

    # Test Markdown formatting
    md_res = format_skill.execute(FormatSkillInput(plan=plan, template_format="markdown"))
    assert isinstance(md_res, FormattedDocumentResponse)
    assert md_res.format_type == "markdown"
    assert "# Meeting Document: Architecture Review" in md_res.content
    assert "## Agenda Breakdown" in md_res.content

    # Test Plain Text formatting
    txt_res = format_skill.execute(FormatSkillInput(plan=plan, template_format="text"))
    assert txt_res.format_type == "text"
    assert "=== MEETING DOCUMENT: ARCHITECTURE REVIEW ===" in txt_res.content

    # Test HTML formatting
    html_res = format_skill.execute(FormatSkillInput(plan=plan, template_format="html"))
    assert html_res.format_type == "html"
    assert "<article class='meeting-plan'>" in html_res.content
