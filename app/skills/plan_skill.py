"""
Lab 3: Skill Creation - Reusable Plan Skill
Implements `skill plan(inputs) -> Plan`: expands inputs into a locked, structured blueprint.
"""

import uuid
from typing import List
from app.skills.base import BaseSkill
from app.models.schemas import (
    PlanSkillInput,
    LockedPlanBlueprint,
    AgendaItem,
    MinutesOutline,
    ActionItemTemplate,
    MeetingPlan,
)


class PlanSkill(BaseSkill[PlanSkillInput, LockedPlanBlueprint]):
    """
    Reusable Plan/Blueprint Skill.
    Constructs a structured, locked meeting blueprint from input parameters.
    Works for any meeting type (committee, standup, sprint_planning, project_sync, etc.)
    without requiring custom code per case.
    """

    name = "plan_skill"
    description = "Turns meeting requirements into a locked, structured plan blueprint."

    def execute(self, inputs: PlanSkillInput) -> LockedPlanBlueprint:
        blueprint_id = f"plan-{uuid.uuid4().hex[:8]}"
        duration = max(15, inputs.duration_minutes)

        # 1. Dynamic agenda distribution based on meeting type & duration
        agenda_items = self._generate_agenda(inputs, duration)

        # 2. Minutes outline synthesis with action item carryover
        minutes_outline = self._generate_minutes_outline(inputs)

        return LockedPlanBlueprint(
            blueprint_id=blueprint_id,
            topic=inputs.topic,
            meeting_type=inputs.meeting_type,
            participants=inputs.participants,
            duration_minutes=duration,
            date_window=inputs.date_window,
            agenda_structure=agenda_items,
            minutes_template=minutes_outline,
            constraints_locked=True,
        )

    def _generate_agenda(self, inputs: PlanSkillInput, total_duration: int) -> List[AgendaItem]:
        meeting_type = (inputs.meeting_type or "general").lower()
        items = []

        # If there are open action items carried over from prior meetings, allocate time for them
        if inputs.prior_action_items:
            action_time = min(15, max(5, total_duration // 4))
            remaining = total_duration - action_time
            items.append(
                AgendaItem(
                    title="Carried-Over Action Items Review",
                    duration_minutes=action_time,
                    objective=f"Review status of {len(inputs.prior_action_items)} open action item(s) from prior meetings.",
                )
            )
        else:
            remaining = total_duration

        if "committee" in meeting_type:
            intro_t = max(5, remaining // 5)
            main_t = max(10, remaining * 3 // 5)
            wrap_t = max(5, remaining - intro_t - main_t)
            items.extend([
                AgendaItem(title="Opening & Agenda Alignment", duration_minutes=intro_t, objective="Confirm agenda, roles, and quorum."),
                AgendaItem(title=f"Core Discussion: {inputs.topic}", duration_minutes=main_t, objective=f"In-depth review and deliberation on {inputs.topic}."),
                AgendaItem(title="Decisions & Next Steps", duration_minutes=wrap_t, objective="Summarize key decisions and assign follow-up owners."),
            ])
        elif "standup" in meeting_type:
            per_person_t = max(2, remaining // max(1, len(inputs.participants)))
            items.extend([
                AgendaItem(title="Participant Status Updates", duration_minutes=per_person_t * len(inputs.participants), objective="Each attendee shares completed tasks, current goals, and blockers."),
                AgendaItem(title="Blocker Triage & Wrap-up", duration_minutes=max(3, remaining - per_person_t * len(inputs.participants)), objective="Identify help needed and clear impediments."),
            ])
        elif "sprint" in meeting_type:
            review_t = remaining // 2
            plan_t = remaining - review_t
            items.extend([
                AgendaItem(title="Sprint Retrospective & Velocity Review", duration_minutes=review_t, objective="Analyze previous sprint performance and learnings."),
                AgendaItem(title=f"Planning: {inputs.topic}", duration_minutes=plan_t, objective="Select backlog items and commit to next sprint goals."),
            ])
        else:  # General / Project Sync
            intro_t = max(5, min(10, int(remaining * 0.2)))
            wrap_t = max(5, min(10, int(remaining * 0.2)))
            main_t = remaining - intro_t - wrap_t
            items.extend([
                AgendaItem(title="Welcome & Context", duration_minutes=intro_t, objective=f"Align team on meeting goals for {inputs.topic}."),
                AgendaItem(title="Core Discussion", duration_minutes=main_t, objective=f"Primary discussion and item reviews for {inputs.topic}."),
                AgendaItem(title="Action Items & Wrap-Up", duration_minutes=wrap_t, objective="Confirm action item owners and target completion dates."),
            ])

        # Guarantee exact total duration sum matching total_duration
        current_sum = sum(item.duration_minutes for item in items)
        if current_sum != total_duration and items:
            diff = total_duration - current_sum
            items[-1].duration_minutes += diff

        return items

    def _generate_minutes_outline(self, inputs: PlanSkillInput) -> MinutesOutline:
        discussion_topics = [
            f"Background and objectives for {inputs.topic}",
            "Key participant contributions and discussion points",
            "Resource, scheduling, or technical constraints identified",
        ]
        key_decisions = [
            f"Approved scope and direction for {inputs.topic}",
        ]

        action_items = []
        if inputs.prior_action_items:
            action_items.extend(inputs.prior_action_items)

        # Always include specific action items for the current meeting topic
        first_owner = inputs.participants[0] if inputs.participants else "Organizer"
        sec_owner = inputs.participants[1] if len(inputs.participants) > 1 else first_owner
        action_items.append(
            ActionItemTemplate(
                description=f"Draft detailed specification for {inputs.topic}",
                owner=first_owner,
                deadline="Next week",
            )
        )
        action_items.append(
            ActionItemTemplate(
                description=f"Follow up on {inputs.topic} action items",
                owner=sec_owner,
                deadline="End of week",
            )
        )

        return MinutesOutline(
            discussion_topics=discussion_topics,
            key_decisions=key_decisions,
            action_items=action_items,
        )


    def to_meeting_plan(self, blueprint: LockedPlanBlueprint) -> MeetingPlan:
        """Helper to convert a LockedPlanBlueprint into a standard MeetingPlan schema."""
        meeting_id = f"mtg-{uuid.uuid4().hex[:8]}"
        return MeetingPlan(
            meeting_id=meeting_id,
            title=blueprint.topic,
            purpose=f"Execute {blueprint.meeting_type} on {blueprint.topic}",
            date=blueprint.date_window,
            duration_minutes=blueprint.duration_minutes,
            participants=blueprint.participants,
            agenda=blueprint.agenda_structure,
            minutes_outline=blueprint.minutes_template,
            assumptions=[
                f"Meeting format locked as '{blueprint.meeting_type}'.",
                f"Agenda dynamically generated for {blueprint.duration_minutes} minute duration.",
            ],
            next_steps=[
                "Submit draft plan for human review and explicit approval.",
                "Execute tool workflow upon approval.",
            ],
            status="draft",
        )
