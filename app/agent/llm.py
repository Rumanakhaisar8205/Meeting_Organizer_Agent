"""
Deterministic Reasoning Engine for Meeting Organizer Agent
Implements Lab 1 reasoning without external LLM APIs.
Uses rule-based semantic analysis and extraction.
"""

import re
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.models.schemas import (
    MeetingPlan,
    AgendaItem,
    MinutesOutline,
    ActionItemTemplate,
    RevisionHistoryEntry,
)


KNOWN_PARTICIPANTS = ["Alice", "Bob", "Charlie", "Dana", "Dr. Meena"]


def parse_participants_input(value: Any) -> List[str]:
    """Parse free-text or list participant input into separate normalized names."""
    if isinstance(value, list):
        parsed: List[str] = []
        for item in value:
            if isinstance(item, str):
                parsed.extend(parse_participants_input(item))
            elif item is not None:
                parsed.append(str(item))
        return _dedupe_participants(parsed)

    if not isinstance(value, str):
        return []

    text = value.strip()
    if not text:
        return []

    text = re.sub(r"\s+and\s+", ",", text, flags=re.IGNORECASE)
    raw_parts = [part.strip() for part in text.split(",") if part.strip()]
    return _dedupe_participants([_normalize_participant_name(part) for part in raw_parts])


def _normalize_participant_name(name: str) -> str:
    """Normalize participant name casing, matching known mock invitees when possible."""
    stripped = name.strip()
    for known in KNOWN_PARTICIPANTS:
        if known.lower() == stripped.lower():
            return known
    return " ".join(word.capitalize() for word in stripped.split())


def _dedupe_participants(names: List[str]) -> List[str]:
    """Preserve order while removing duplicate participants (case-insensitive)."""
    seen = set()
    unique: List[str] = []
    for name in names:
        key = name.lower()
        if key not in seen:
            seen.add(key)
            unique.append(name)
    return unique


class AnalysisResult(BaseModel):
    extracted_topic: Optional[str] = None
    extracted_participants: Optional[List[str]] = None
    extracted_duration: Optional[int] = None
    extracted_date: Optional[str] = None
    missing_fields: List[str] = Field(default_factory=list)
    clarification_questions: List[str] = Field(default_factory=list)
    reasoning: str = ""


class DeterministicReasoningEngine:
    """
    Reasoning engine using deterministic rule-based extraction.
    No external LLM APIs required. Runs completely locally.
    """

    DURATION_PATTERN = re.compile(
        r'^\s*(\d+(?:\.\d+)?)\s*(?:hour|hr|h|min|minute|m)s?\s*$',
        re.IGNORECASE,
    )

    def __init__(self):
        pass

    def _is_duration_expression(self, text: str) -> bool:
        """Return True when text is solely a duration phrase (e.g. '20 mins', '1 hour')."""
        if not text or not text.strip():
            return False
        return bool(self.DURATION_PATTERN.match(text.strip()))

    def _extract_duration_minutes(self, text: str) -> Optional[int]:
        """Extract duration in minutes from text; returns None if not a duration phrase."""
        t_lower = text.lower()
        hour_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:hour|hr|h)s?\b', t_lower)
        if hour_match:
            return int(float(hour_match.group(1)) * 60)
        min_match = re.search(r'(\d+)\s*(?:min|minute|m)s?\b', t_lower)
        if min_match:
            return int(min_match.group(1))
        return None

    def _trim_topic_candidate(self, candidate: str) -> str:
        """Strip trailing date/duration fragments accidentally captured with a topic phrase."""
        days = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
        trimmed = candidate.strip()
        stop_patterns = [
            rf'\s+\bnext\s+(?:{days})\b.*',
            rf'\s+\b(?:{days})\b.*',
            r'\s+\bfor\s+\d+(?:\.\d+)?\s*(?:hours?|hrs?|h|mins?|minutes?)\b.*',
            r'\s+\bon\s+\d{4}-\d{2}-\d{2}\b.*',
            r'\s+\btomorrow\b.*',
            r'\s+\bnext\s+week\b.*',
        ]
        for pattern in stop_patterns:
            trimmed = re.sub(pattern, '', trimmed, flags=re.IGNORECASE).strip()
        return trimmed

    def analyze_request(self, text: str, current_goal: Dict[str, Any]) -> AnalysisResult:
        """
        Analyze free-text user request using rule-based extraction.
        Identify genuinely missing fields and generate contextual clarification questions.
        """
        t_clean = text.strip()
        t_lower = t_clean.lower()
        extracted: Dict[str, Any] = {}
        reasoning_steps = []

        # 1. Duration Extraction (before topic to avoid misclassifying "for 20 mins")
        duration = current_goal.get("duration_minutes")
        if not duration and t_clean:
            parsed_duration = self._extract_duration_minutes(t_clean)
            if parsed_duration:
                duration = parsed_duration
                reasoning_steps.append(f"Extracted duration: {duration} minutes")

        if duration:
            extracted["duration_minutes"] = duration

        # 2. Topic Extraction
        topic = current_goal.get("topic")
        if not topic and t_clean:
            # Check for explicit keywords
            topic_keywords = [
                ("project planning", "Project Planning"),
                ("sprint planning", "Sprint Planning"),
                ("sprint sync", "Sprint Sync"),
                ("architecture review", "Architecture Review"),
                ("design sync", "Design Sync"),
                ("code review", "Code Review"),
                ("budget discussion", "Budget Discussion"),
                ("status update", "Status Update"),
                ("catchup", "Team Catchup"),
                ("project sync", "Project Sync"),
                ("standup", "Standup Meeting"),
                ("retrospective", "Sprint Retrospective"),
                ("demo", "Product Demo"),
                ("sync", "Sync Meeting"),
                ("review", "Review Meeting"),
            ]
            for kw, title in topic_keywords:
                if kw in t_lower:
                    topic = title
                    reasoning_steps.append(f"Identified topic keyword: '{kw}' -> '{title}'")
                    break

            # Check for contextual clauses (exclude duration expressions)
            if not topic:
                discuss_match = re.search(
                    r'(?:about|for|regarding|discussing|discuss|to discuss)\s+([^,\.\n\?]+)',
                    t_clean,
                    re.IGNORECASE,
                )
                if discuss_match:
                    candidate = self._trim_topic_candidate(discuss_match.group(1).strip())
                    if candidate and not self._is_duration_expression(candidate) and len(candidate) > 2:
                        topic = candidate[0].upper() + candidate[1:] if len(candidate) > 0 else candidate
                        reasoning_steps.append(f"Extracted topic from contextual phrase: '{topic}'")

        if topic and not self._is_duration_expression(topic):
            extracted["topic"] = topic

        # 3. Participants Extraction (improved to handle arbitrary names)
        participants = current_goal.get("participants")
        if not participants:
            # First check known mock data participants
            known_candidates = ["Alice", "Bob", "Charlie", "Dana", "Dr. Meena"]
            found = []
            for name in known_candidates:
                if re.search(rf'\b{re.escape(name)}\b', t_clean, re.IGNORECASE):
                    found.append(name)

            # If no known names found, try to extract capitalized names
            if not found:
                # Look for capitalized words that might be names
                name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
                potential_names = re.findall(name_pattern, t_clean)

                # Filter out common non-name words
                non_names = {
                    'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
                    'January', 'February', 'March', 'April', 'May', 'June',
                    'July', 'August', 'September', 'October', 'November', 'December',
                    'Architecture', 'Review', 'Sprint', 'Sync', 'Meeting', 'Design',
                    'Code', 'Status', 'Update', 'Team', 'Catchup', 'Demo', 'Budget',
                    'Discussion', 'Planning', 'Retrospective', 'Schedule', 'Discuss'
                }

                for name in potential_names:
                    if name not in non_names and name not in found:
                        found.append(name)
                        reasoning_steps.append(f"Extracted participant name: '{name}'")

            if found:
                participants = found
                if reasoning_steps[-1] != f"Extracted participants: {participants}":
                    reasoning_steps.append(f"Identified participants: {found}")

        if participants:
            extracted["participants"] = participants

        # 4. Date Window Extraction
        date_window = current_goal.get("date_window")
        if not date_window and t_clean:
            # Check for ISO dates (YYYY-MM-DD)
            iso_match = re.search(r'\b(202\d-\d{2}-\d{2})\b', t_clean)
            if iso_match:
                date_window = iso_match.group(1)
                reasoning_steps.append(f"Extracted ISO date: {date_window}")
            else:
                days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                # Prefer "next <Day>" when present
                next_day_match = re.search(
                    rf'\bnext\s+({"|".join(days)})\b',
                    t_clean,
                    re.IGNORECASE,
                )
                if next_day_match:
                    date_window = f"Next {next_day_match.group(1).capitalize()}"
                    reasoning_steps.append(f"Extracted relative day: {date_window}")
                else:
                    for day in days:
                        if re.search(rf'\b{day}\b', t_clean, re.IGNORECASE):
                            date_window = day
                            reasoning_steps.append(f"Extracted day of week: {date_window}")
                            break

                # Check for relative dates
                if not date_window:
                    if re.search(r'\btomorrow\b', t_lower):
                        date_window = "Tomorrow"
                        reasoning_steps.append("Extracted relative date: Tomorrow")
                    elif re.search(r'\bnext\s+week\b', t_lower):
                        date_window = "Next Week"
                        reasoning_steps.append("Extracted relative date: Next Week")

        if date_window:
            extracted["date_window"] = date_window

        # Merge extracted values with existing goal state for completeness checks
        final_topic = extracted.get("topic") or current_goal.get("topic")
        if final_topic and self._is_duration_expression(final_topic):
            final_topic = current_goal.get("topic") if current_goal.get("topic") and not self._is_duration_expression(current_goal.get("topic")) else None

        final_participants = extracted.get("participants") or current_goal.get("participants")
        final_duration = extracted.get("duration_minutes") or current_goal.get("duration_minutes")
        final_date = extracted.get("date_window") or current_goal.get("date_window")

        # Identify missing fields dynamically (only genuinely missing)
        missing = []
        if not final_topic:
            missing.append("topic")
        if not final_participants:
            missing.append("participants")
        if not final_duration:
            missing.append("duration_minutes")
        if not final_date:
            missing.append("date_window")

        reasoning = "; ".join(reasoning_steps) if reasoning_steps else "Analysis complete."

        # Generate contextual clarification questions
        dynamic_questions = self._generate_clarification_questions(missing, text)

        return AnalysisResult(
            extracted_topic=final_topic if final_topic else None,
            extracted_participants=final_participants if final_participants else None,
            extracted_duration=final_duration if final_duration else None,
            extracted_date=final_date if final_date else None,
            missing_fields=missing,
            clarification_questions=dynamic_questions,
            reasoning=reasoning,
        )

    def _generate_clarification_questions(self, missing_fields: List[str], user_text: str) -> List[str]:
        """Generate contextual clarification questions based on missing fields."""
        if not missing_fields:
            return []

        questions = []
        field_to_question = {
            "topic": "What would you like to discuss in this meeting?",
            "participants": "Who should attend this meeting?",
            "duration_minutes": "How long should this meeting be (in minutes)?",
            "date_window": "When would you like to schedule this (date or day)?",
        }

        for field in missing_fields:
            if field in field_to_question:
                questions.append(field_to_question[field])

        return questions

    def _compute_standard_agenda_durations(self, duration: int) -> Dict[str, int]:
        """Compute intro/core/wrap agenda segment durations for a meeting length."""
        intro_mins = max(5, min(10, int(duration * 0.2)))
        wrap_mins = max(5, min(10, int(duration * 0.2)))
        core_mins = max(10, duration - intro_mins - wrap_mins)
        return {
            "Welcome & Context": intro_mins,
            "Core Discussion": core_mins,
            "Action Items & Wrap-Up": wrap_mins,
        }

    def _recalculate_agenda_durations(self, agenda: List[AgendaItem], duration: int) -> None:
        """Update agenda item durations so their total equals the meeting duration."""
        if not agenda:
            return

        standard_durations = self._compute_standard_agenda_durations(duration)
        standard_titles = set(standard_durations.keys())
        extra_items = [item for item in agenda if item.title not in standard_titles]

        if not extra_items and standard_titles.issubset({item.title for item in agenda}):
            for item in agenda:
                if item.title in standard_durations:
                    item.duration_minutes = standard_durations[item.title]
            return

        old_total = sum(item.duration_minutes for item in agenda)
        if old_total <= 0:
            return

        scaled = [max(1, round(item.duration_minutes * duration / old_total)) for item in agenda]
        diff = duration - sum(scaled)
        if diff != 0:
            core_idx = next(
                (i for i, item in enumerate(agenda) if item.title == "Core Discussion"),
                len(agenda) // 2,
            )
            scaled[core_idx] = max(1, scaled[core_idx] + diff)

        for item, mins in zip(agenda, scaled):
            item.duration_minutes = mins

    def generate_draft_plan(self, goal: Dict[str, Any]) -> MeetingPlan:
        """
        Generate a structured DRAFT MeetingPlan from collected requirements.
        Critically: Does NOT fabricate availability, slots, or preferences.
        """
        topic = goal.get("topic") or "Team Meeting"
        participants = goal.get("participants") or []
        duration = goal.get("duration_minutes") or 30
        date = goal.get("date_window") or "Unspecified Date"

        standard_durations = self._compute_standard_agenda_durations(duration)

        agenda = [
            AgendaItem(
                title=f"Welcome & Context",
                duration_minutes=standard_durations["Welcome & Context"],
                objective="Align on meeting goals and scope.",
            ),
            AgendaItem(
                title="Core Discussion",
                duration_minutes=standard_durations["Core Discussion"],
                objective="Review details and address key questions.",
            ),
            AgendaItem(
                title="Action Items & Wrap-Up",
                duration_minutes=standard_durations["Action Items & Wrap-Up"],
                objective="Summarize decisions and confirm next steps.",
            ),
        ]

        # Assign default owners
        lead = participants[0] if participants else "Organizer"
        sec = participants[1] if len(participants) > 1 else lead

        minutes_outline = MinutesOutline(
            discussion_topics=[f"Context and scope of {topic}"],
            key_decisions=["Confirmed direction and responsibilities"],
            action_items=[
                ActionItemTemplate(
                    description=f"Prepare summary notes for {topic}",
                    owner=lead,
                    deadline="Within 24 hours",
                ),
                ActionItemTemplate(
                    description="Follow up on action items",
                    owner=sec if sec != lead else lead,
                    deadline="End of week",
                ),
            ],
        )

        assumptions = [
            "This is a DRAFT plan based on your requirements.",
            "Participant availability and time slots are NOT assumed—they will be verified through Lab 2 tools upon approval.",
        ]

        next_steps = [
            "1. Review this draft plan.",
            "2. Approve to proceed with Lab 2 scheduling.",
            "3. Tools will verify availability and find collision-free time slots.",
        ]

        meeting_id = f"MP-{uuid.uuid4().hex[:8].upper()}"

        return MeetingPlan(
            meeting_id=meeting_id,
            title=f"{topic}",
            purpose=f"Coordinate and align on {topic}",
            date=date,
            time_slot="PENDING_VERIFICATION (Awaiting approval and Lab 2 tool execution)",
            verified_candidate_slots=[],
            duration_minutes=duration,
            participants=participants,
            agenda=agenda,
            minutes_outline=minutes_outline,
            assumptions=assumptions,
            next_steps=next_steps,
            status="waiting_for_approval",
            revision_count=0,
            revision_history=[],
        )

    def revise_plan(
        self,
        current_plan: MeetingPlan,
        feedback: str,
        current_goal: Dict[str, Any],
    ) -> Tuple[MeetingPlan, List[str]]:
        """
        Mutate the existing plan in-place based on feedback.
        Preserves all unchanged fields and records mutations in revision history.
        """
        f_clean = feedback.strip()
        f_lower = f_clean.lower()
        mutations: List[str] = []

        # 1. Duration changes
        dur_match = re.search(r'(\d+)\s*(?:min|minute|m)s?\b', f_lower)
        if dur_match and any(word in f_lower for word in ["duration", "make", "length", "minutes", "change"]):
            new_dur = int(dur_match.group(1))
            current_plan.duration_minutes = new_dur
            current_goal["duration_minutes"] = new_dur
            self._recalculate_agenda_durations(current_plan.agenda, new_dur)
            mutations.append(f"Updated duration to {new_dur} minutes and recalculated agenda durations")

        # 2. Date changes
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for day in days:
            if day.lower() in f_lower and any(w in f_lower for w in ["move", "reschedule", "on", "to"]):
                current_plan.date = day
                current_goal["date_window"] = day
                mutations.append(f"Updated date to {day}")
                break

        iso_match = re.search(r'\b(202\d-\d{2}-\d{2})\b', f_clean)
        if iso_match:
            current_plan.date = iso_match.group(1)
            current_goal["date_window"] = iso_match.group(1)
            mutations.append(f"Updated date to {iso_match.group(1)}")

        # 3. Participant changes
        known_names = ["Alice", "Bob", "Charlie", "Dana", "Dr. Meena"]
        for name in known_names:
            if any(p in f_lower for p in [f"add {name.lower()}", f"include {name.lower()}", f"invite {name.lower()}"]):
                if name not in current_plan.participants:
                    current_plan.participants.append(name)
                    mutations.append(f"Added participant: {name}")
            elif any(p in f_lower for p in [f"remove {name.lower()}", f"exclude {name.lower()}"]):
                if name in current_plan.participants:
                    current_plan.participants.remove(name)
                    mutations.append(f"Removed participant: {name}")

        # 4. Topic changes
        topic_match = re.search(
            r'(?:topic|discuss|discussion|subject|about)\s+(?:to|is|should be|:)?\s*["\']?([^"\']+)["\']?',
            f_clean,
            re.IGNORECASE,
        )
        if topic_match:
            new_topic = topic_match.group(1).strip().rstrip(".")
            if new_topic and not self._is_duration_expression(new_topic):
                current_plan.title = new_topic
                current_plan.purpose = f"Coordinate and align on {new_topic}"
                current_goal["topic"] = new_topic
                current_plan.minutes_outline.discussion_topics = [f"Context and scope of {new_topic}"]
                if current_plan.minutes_outline.action_items:
                    current_plan.minutes_outline.action_items[0].description = (
                        f"Prepare summary notes for {new_topic}"
                    )
                mutations.append(f"Updated topic to '{new_topic}'")

        # 5. Agenda changes
        if "security" in f_lower and any(w in f_lower for w in ["add", "include", "agenda"]):
            current_plan.agenda.append(
                AgendaItem(
                    title="Security & Compliance Review",
                    duration_minutes=15,
                    objective="Identify and mitigate potential risks.",
                )
            )
            mutations.append("Added agenda item: Security & Compliance Review")

        if not mutations:
            mutations = [f"Recorded feedback: {f_clean}"]

        # Record revision
        current_plan.revision_count += 1
        current_plan.status = "waiting_for_approval"

        history_entry = RevisionHistoryEntry(
            revision_number=current_plan.revision_count,
            feedback=f_clean,
            mutations=mutations,
            timestamp=datetime.now().isoformat(timespec="seconds"),
        )
        current_plan.revision_history.append(history_entry)

        return current_plan, mutations


# Backward-compatible alias for legacy imports
LLMReasoningEngine = DeterministicReasoningEngine

# Global instance
llm_engine = DeterministicReasoningEngine()
