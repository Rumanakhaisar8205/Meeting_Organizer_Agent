"""
Lab 3: Skill Creation - Reusable Formatting Skill
Implements `skill format_scheduled(result, template) -> Document`: renders formatted meeting documents.
"""

from app.skills.base import BaseSkill
from app.models.schemas import FormatSkillInput, FormattedDocumentResponse, MeetingPlan


class FormatSkill(BaseSkill[FormatSkillInput, FormattedDocumentResponse]):
    """
    Reusable Formatting & Assembly Skill.
    Renders a structured MeetingPlan into clean Markdown, Plain Text, or HTML documents.
    Works for any case without code changes.
    """

    name = "format_skill"
    description = "Formats a MeetingPlan into standardized Markdown, Text, or HTML documents."

    def execute(self, inputs: FormatSkillInput) -> FormattedDocumentResponse:
        plan: MeetingPlan = inputs.plan
        fmt = (inputs.template_format or "markdown").lower()

        if fmt == "html":
            content, sections = self._format_html(plan, inputs.include_minutes_template)
        elif fmt == "text":
            content, sections = self._format_text(plan, inputs.include_minutes_template)
        else:  # Default to markdown
            content, sections = self._format_markdown(plan, inputs.include_minutes_template)

        return FormattedDocumentResponse(
            format_type=fmt,
            content=content,
            sections=sections,
        )

    def _format_markdown(self, plan: MeetingPlan, include_minutes: bool) -> tuple[str, dict[str, str]]:
        sections = {}

        # Header Section
        header = (
            f"# Meeting Document: {plan.title}\n\n"
            f"- **Meeting ID:** `{plan.meeting_id}`\n"
            f"- **Status:** {plan.status.upper()}\n"
            f"- **Date Window:** {plan.date}\n"
            f"- **Time Slot:** {plan.time_slot}\n"
            f"- **Duration:** {plan.duration_minutes} minutes\n"
            f"- **Participants:** {', '.join(plan.participants)}\n"
            f"- **Purpose:** {plan.purpose}\n"
        )
        sections["Header"] = header

        # Agenda Section
        agenda_lines = ["## Agenda Breakdown\n", "| # | Topic | Duration | Objective |", "|---|---|---|---|"]
        for idx, item in enumerate(plan.agenda, 1):
            agenda_lines.append(f"| {idx} | {item.title} | {item.duration_minutes}m | {item.objective} |")
        agenda_sec = "\n".join(agenda_lines) + "\n"
        sections["Agenda"] = agenda_sec

        # Minutes Outline Section
        minutes_sec = ""
        if include_minutes and plan.minutes_outline:
            m_lines = ["## Minutes Outline & Action Items\n"]
            if plan.minutes_outline.discussion_topics:
                m_lines.append("### Discussion Topics")
                for t in plan.minutes_outline.discussion_topics:
                    m_lines.append(f"- {t}")
                m_lines.append("")
            if plan.minutes_outline.key_decisions:
                m_lines.append("### Key Decisions")
                for d in plan.minutes_outline.key_decisions:
                    m_lines.append(f"- [DECISION] {d}")
                m_lines.append("")
            if plan.minutes_outline.action_items:
                m_lines.append("### Action Items")
                m_lines.append("| Description | Owner | Deadline |")
                m_lines.append("|---|---|---|")
                for ai in plan.minutes_outline.action_items:
                    m_lines.append(f"| {ai.description} | {ai.owner} | {ai.deadline} |")
                m_lines.append("")
            minutes_sec = "\n".join(m_lines)
            sections["Minutes"] = minutes_sec

        # Next Steps & Assumptions
        next_lines = ["## Next Steps & Assumptions\n", "### Assumptions"]
        for a in plan.assumptions:
            next_lines.append(f"- {a}")
        next_lines.append("\n### Next Steps")
        for ns in plan.next_steps:
            next_lines.append(f"1. {ns}")
        next_sec = "\n".join(next_lines) + "\n"
        sections["Next Steps"] = next_sec

        full_content = "\n".join(filter(None, [header, agenda_sec, minutes_sec, next_sec]))
        return full_content, sections

    def _format_text(self, plan: MeetingPlan, include_minutes: bool) -> tuple[str, dict[str, str]]:
        sections = {}
        header = (
            f"=== MEETING DOCUMENT: {plan.title.upper()} ===\n"
            f"ID: {plan.meeting_id} | STATUS: {plan.status.upper()}\n"
            f"Date: {plan.date} | Time Slot: {plan.time_slot} | Duration: {plan.duration_minutes}m\n"
            f"Participants: {', '.join(plan.participants)}\n"
            f"Purpose: {plan.purpose}\n"
        )
        sections["Header"] = header

        agenda_lines = ["--- AGENDA ---"]
        for idx, item in enumerate(plan.agenda, 1):
            agenda_lines.append(f"{idx}. {item.title} ({item.duration_minutes}m): {item.objective}")
        agenda_sec = "\n".join(agenda_lines) + "\n"
        sections["Agenda"] = agenda_sec

        minutes_sec = ""
        if include_minutes and plan.minutes_outline:
            m_lines = ["--- MINUTES OUTLINE ---"]
            for t in plan.minutes_outline.discussion_topics:
                m_lines.append(f"* Topic: {t}")
            for d in plan.minutes_outline.key_decisions:
                m_lines.append(f"* Decision: {d}")
            for ai in plan.minutes_outline.action_items:
                m_lines.append(f"* Action Item: {ai.description} [Owner: {ai.owner}, Due: {ai.deadline}]")
            minutes_sec = "\n".join(m_lines) + "\n"
            sections["Minutes"] = minutes_sec

        full_content = "\n".join(filter(None, [header, agenda_sec, minutes_sec]))
        return full_content, sections

    def _format_html(self, plan: MeetingPlan, include_minutes: bool) -> tuple[str, dict[str, str]]:
        sections = {}
        header = (
            f"<div class='meeting-header'>\n"
            f"  <h1>{plan.title}</h1>\n"
            f"  <p><strong>ID:</strong> {plan.meeting_id} | <strong>Status:</strong> {plan.status}</p>\n"
            f"  <p><strong>Date:</strong> {plan.date} | <strong>Slot:</strong> {plan.time_slot}</p>\n"
            f"  <p><strong>Participants:</strong> {', '.join(plan.participants)}</p>\n"
            f"</div>\n"
        )
        sections["Header"] = header

        agenda_rows = "".join(
            f"<tr><td>{i}</td><td>{item.title}</td><td>{item.duration_minutes}m</td><td>{item.objective}</td></tr>"
            for i, item in enumerate(plan.agenda, 1)
        )
        agenda_sec = f"<div class='agenda'><h2>Agenda</h2><table>{agenda_rows}</table></div>\n"
        sections["Agenda"] = agenda_sec

        full_content = f"<article class='meeting-plan'>\n{header}\n{agenda_sec}\n</article>"
        return full_content, sections
