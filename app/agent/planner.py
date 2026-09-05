"""
Meeting Organizer Agent
Implements the deterministic Goal-Plan-Act-Observe-Revise drafting loop and
Lab 2 tool-using verification flow with an explicit approval gate.
"""

from typing import Dict, Any, List, Optional, Tuple
from app.models.schemas import (
    AgentPhase,
    MeetingPlan,
    RevisionHistoryEntry,
)
from app.tools.executor import ToolExecutor
from app.agent.llm import llm_engine, AnalysisResult, parse_participants_input
from app.tools.calculator_tool import rank_meeting_slots


TOP_K_SLOTS = 3


class MeetingOrganizerAgent:
    """
    Coordinator and Planner Agent for organizing meetings.
    Operates on a structured goal predicate and maintains strict phase transitions:
    CLARIFICATION -> DRAFT_GENERATION -> WAITING_FOR_APPROVAL -> REVISION -> TOOL_EXECUTION -> COMPLETED
    """

    def __init__(self, executor: Optional[ToolExecutor] = None):
        # Goal modeled as structured data -- a checkable predicate, not prose
        self.goal: Dict[str, Any] = {
            "topic": None,
            "participants": None,
            "duration_minutes": None,
            "date_window": None,
            "draft_generated": False,
            "is_approved": False,
            "plan_generated": False,
        }
        self.phase: AgentPhase = AgentPhase.CLARIFICATION
        self.executor = executor or ToolExecutor()
        self.plan: Optional[MeetingPlan] = None
        self.log: List[Dict[str, Any]] = []
        self.latest_analysis: Optional[AnalysisResult] = None

    # ---- Goal check predicates ------------------------------------------
    def is_draft_ready(self) -> bool:
        """Lab 1 Goal check: True when draft plan is generated and awaiting approval."""
        return self.goal["draft_generated"] is True and self.phase == AgentPhase.WAITING_FOR_APPROVAL

    def satisfied(self) -> bool:
        """Declared final stopping condition: True when plan is verified by tools post-approval."""
        return self.goal["plan_generated"] is True and self.phase == AgentPhase.COMPLETED

    # ---- Planner: decide the next step ----------------------------------
    def next_step(self) -> Tuple[str, Optional[str]]:
        """
        Inspect goal fields dynamically; ask only for genuinely missing details.
        Does not execute a fixed questionnaire.
        """
        for field in ("topic", "participants", "duration_minutes", "date_window"):
            if self.goal.get(field) is None:
                return ("ask", field)
        
        if not self.goal["draft_generated"]:
            return ("generate_draft", None)
        
        if not self.goal["is_approved"]:
            return ("await_approval", None)
            
        if not self.goal["plan_generated"]:
            return ("execute_tools", None)

        return ("done", None)

    # ---- Centralized tool execution choke point -------------------------
    def _call(self, tool_name: str, reason: str, **kwargs) -> Dict[str, Any]:
        """
        Centralized choke point delegating to ToolExecutor.
        Logs tool name, reason, inputs, and outputs, raising on errors (Lab 2).
        """
        return self.executor.execute(tool_name, reason=reason, **kwargs)

    # ---- Structured Extraction and Analysis -----------------------------
    def extract_from_text(self, text: str) -> Dict[str, Any]:
        """
        Analyze user text using deterministic rule-based extraction to identify missing info.
        """
        analysis = llm_engine.analyze_request(text, self.goal)
        self.latest_analysis = analysis

        if analysis.extracted_topic:
            self.goal["topic"] = analysis.extracted_topic
        if analysis.extracted_participants:
            self.goal["participants"] = analysis.extracted_participants
        if analysis.extracted_duration:
            self.goal["duration_minutes"] = analysis.extracted_duration
        if analysis.extracted_date:
            self.goal["date_window"] = analysis.extracted_date

        return {
            "topic": self.goal["topic"],
            "participants": self.goal["participants"],
            "duration_minutes": self.goal["duration_minutes"],
            "date_window": self.goal["date_window"],
            "missing_fields": analysis.missing_fields,
            "clarification_questions": analysis.clarification_questions,
            "reasoning": analysis.reasoning,
        }

    # ---- Clarification questions generator ------------------------------
    def get_missing_clarification_questions(self) -> List[str]:
        """Return dynamic clarification questions from deterministic analysis."""
        if self.latest_analysis and self.latest_analysis.clarification_questions:
            return self.latest_analysis.clarification_questions
        analysis = llm_engine.analyze_request("", self.goal)
        return analysis.clarification_questions

    # ---- Ingestion of clarification responses ---------------------------
    def apply_clarification(self, answers: Dict[str, Any]) -> None:
        """Update goal fields from user answers to clarification questions."""
        for field, value in answers.items():
            if field in self.goal and field not in ("draft_generated", "is_approved", "plan_generated") and value is not None:
                if field == "duration_minutes":
                    self.goal[field] = int(value)
                elif field == "participants":
                    self.goal[field] = parse_participants_input(value)
                else:
                    self.goal[field] = value

        # Re-evaluate analysis
        self.latest_analysis = llm_engine.analyze_request("", self.goal)

    # ---- Lab 1 Core Loop: Goal -> Plan -> Act -> Observe ----------------
    def run(self, user_answers: Optional[Dict[str, Any]] = None) -> Optional[MeetingPlan]:
        """
        Run the Lab 1 planning loop to produce a structured DRAFT MeetingPlan.
        Stops at WAITING_FOR_APPROVAL until user explicitly approves.
        """
        if user_answers:
            self.apply_clarification(user_answers)

        while True:
            step, arg = self.next_step()

            if step == "ask":
                self.phase = AgentPhase.CLARIFICATION
                questions = self.get_missing_clarification_questions()
                question_text = questions[0] if questions else f"Please provide {arg}"
                self.log.append({
                    "iteration": len(self.log) + 1,
                    "planned": f"ask for {arg}",
                    "action": f"asked user for {arg} ('{question_text}')",
                    "observed": None,
                    "stopped": True,
                    "stop_reason": f"awaiting clarification for missing field: {arg}",
                })
                return None

            elif step == "generate_draft":
                self.phase = AgentPhase.DRAFT_GENERATION
                self.log.append({
                    "iteration": len(self.log) + 1,
                    "planned": "synthesize draft meeting plan using gathered requirements",
                    "action": "deterministic planner generated structured draft plan from completed goal state",
                    "observed": None,
                    "stopped": False,
                })
                
                # Generate draft plan without fabricated time slots
                self.plan = llm_engine.generate_draft_plan(self.goal)
                self.goal["draft_generated"] = True
                self.phase = AgentPhase.WAITING_FOR_APPROVAL

                self.log.append({
                    "iteration": len(self.log) + 1,
                    "planned": "present draft meeting plan for human review and approval",
                    "action": "draft plan generated and presented to user",
                    "observed": self.plan.model_dump(),
                    "stopped": True,
                    "stop_reason": "draft generated; waiting for human approval or revision",
                })
                return self.plan

            elif step == "await_approval":
                self.phase = AgentPhase.WAITING_FOR_APPROVAL
                return self.plan

            elif step == "execute_tools":
                # User has approved -> run Lab 2 tools
                return self._execute_lab2_tool_flow()

            elif step == "done":
                self.phase = AgentPhase.COMPLETED
                return self.plan

    # ---- Lab 1 Revision: In-Place Mutation on Feedback ------------------
    def revise(self, feedback: str) -> MeetingPlan:
        """
        Apply user feedback by mutating the existing self.plan object in-place.
        Preserves unchanged fields and updates revision_history without restarting from scratch.
        """
        if self.plan is None:
            raise RuntimeError("Cannot revise a non-existent plan. Generate a draft plan first.")

        self.phase = AgentPhase.REVISION

        # Iteration Log: Feedback received
        self.log.append({
            "iteration": len(self.log) + 1,
            "planned": "apply user feedback to existing plan",
            "action": f"feedback received: '{feedback}'",
            "observed": None,
            "stopped": False,
        })

        # Deterministic planner updates the existing plan in place and records history
        mutated_plan, mutation_descriptions = llm_engine.revise_plan(
            current_plan=self.plan,
            feedback=feedback,
            current_goal=self.goal,
        )
        self.plan = mutated_plan
        self.phase = AgentPhase.WAITING_FOR_APPROVAL

        # Iteration Log: Confirm mutation without restart
        self.log.append({
            "iteration": len(self.log) + 1,
            "planned": "confirm revised draft plan",
            "action": f"mutated existing plan in-place (not regenerated from scratch): {', '.join(mutation_descriptions)}",
            "observed": self.plan.model_dump(),
            "stopped": True,
            "stop_reason": "revision applied without restarting the loop",
        })

        return self.plan

    # ---- Lab 2 Approval Gate & Tool Execution ---------------------------
    def approve_draft(self, notes: Optional[str] = None) -> MeetingPlan:
        """
        Explicit user approval gate.
        Triggers transition from Lab 1 (Drafting) to Lab 2 (Tool Execution & Verification).
        """
        if self.plan is None:
            raise RuntimeError("Cannot approve: No draft plan exists.")
        if self.phase != AgentPhase.WAITING_FOR_APPROVAL:
            raise RuntimeError("Cannot approve: Draft plan must be waiting for explicit user approval.")

        self.goal["is_approved"] = True
        self.phase = AgentPhase.TOOL_EXECUTION

        self.log.append({
            "iteration": len(self.log) + 1,
            "planned": "process explicit user approval of draft plan",
            "action": f"user approved draft plan (notes: '{notes or 'None'}'); proceeding to Lab 2 tool execution",
            "observed": {"is_approved": True},
            "stopped": False,
        })

        return self._execute_lab2_tool_flow()

    def _execute_lab2_tool_flow(self) -> MeetingPlan:
        """
        Execute Lab 2 tool chain:
        1. Read invitee preferences for all participants
        2. Read calendars for all participants
        3. Calculate verified common meeting slots
        4. Finalize MeetingPlan with genuine verified slot
        """
        participants = self.plan.participants
        date = self.plan.date
        duration = self.plan.duration_minutes

        # Step 1: Query Invitee Preferences
        invitee_profiles = {}
        for p in participants:
            self.log.append({
                "iteration": len(self.log) + 1,
                "planned": f"query invitee preferences for {p}",
                "action": f"tool call: read_invitee_preferences(participant='{p}')",
                "observed": None,
                "stopped": False,
            })
            pref_result = self._call(
                "read_invitee_preferences",
                reason=f"inspect working hours, timezone, and buffer preferences for {p}",
                participant=p,
            )
            invitee_profiles[p] = pref_result
            self.log[-1]["observed"] = pref_result

        # Step 2: Query Calendars
        calendars = {}
        for p in participants:
            self.log.append({
                "iteration": len(self.log) + 1,
                "planned": f"query calendar availability for {p} on {date}",
                "action": f"tool call: read_calendar(participant='{p}', date='{date}')",
                "observed": None,
                "stopped": False,
            })
            cal_result = self._call(
                "read_calendar",
                reason=f"retrieve booked events and busy intervals for {p} on {date}",
                participant=p,
                date=date,
            )
            calendars[p] = cal_result
            self.log[-1]["observed"] = cal_result

        # Step 3: Tool Chaining -- Calculate Meeting Slots
        self.log.append({
            "iteration": len(self.log) + 1,
            "planned": f"calculate verified collision-free slots for {participants} on {date}",
            "action": f"tool call: calculate_meeting_slots(participants={participants}, date='{date}', duration_minutes={duration})",
            "observed": None,
            "stopped": False,
        })
        slots_result = self._call(
            "calculate_meeting_slots",
            reason="find mutually available collision-free continuous time slots using verified ground-truth data",
            participants=participants,
            date=date,
            duration_minutes=duration,
        )
        self.log[-1]["observed"] = slots_result

        # Step 4: Rank verified slots and present Top-K for user selection
        available_slots = slots_result.get("available_slots", [])
        ranked_slots = rank_meeting_slots(available_slots, participants)
        top_k_slots = ranked_slots[:TOP_K_SLOTS]
        self.plan.verified_candidate_slots = top_k_slots

        if top_k_slots:
            self.plan.time_slot = "AWAITING_USER_SLOT_SELECTION"
            self.plan.status = "awaiting_slot_selection"
            self.plan.assumptions = [
                f"Verified: {len(available_slots)} collision-free slot(s) found on {date} for {', '.join(participants)}.",
                f"Top {len(top_k_slots)} options ranked by invitee preferences are presented for selection.",
                "Timezone UTC+0 applied.",
            ]
            self.plan.next_steps = [
                f"Select your preferred time slot from the Top-{len(top_k_slots)} options.",
                "After selection, calendar invitations will be prepared.",
            ]
            self.phase = AgentPhase.SLOT_SELECTION
        else:
            self.plan.time_slot = "NO_COMMON_SLOT_AVAILABLE (Schedule conflict detected across participants)"
            self.plan.status = "unresolved_conflict"
            self.plan.assumptions = [
                f"CONFLICT DETECTED: No collision-free slot of {duration} minutes exists on {date} for {', '.join(participants)}.",
                "Manual rescheduling or participant adjustment required.",
            ]
            self.plan.next_steps = [
                "Review participant calendar busy intervals.",
                "Adjust meeting duration or propose an alternative date.",
            ]
            self.goal["plan_generated"] = True
            self.phase = AgentPhase.COMPLETED

        self.log.append({
            "iteration": len(self.log) + 1,
            "planned": "rank verified slots and present Top-K options",
            "action": f"ranked {len(available_slots)} verified slot(s); presenting Top-{len(top_k_slots)} for user selection",
            "observed": self.plan.model_dump(),
            "stopped": top_k_slots != [],
            "stop_reason": "awaiting user slot selection" if top_k_slots else "no common slots available",
        })

        return self.plan

    def select_time_slot(self, choice: int) -> MeetingPlan:
        """
        Apply the user's Top-K slot selection to the existing MeetingPlan.
        Marks the plan as confirmed without creating a new meeting ID.
        """
        if self.plan is None:
            raise RuntimeError("Cannot select slot: No meeting plan exists.")
        if self.phase != AgentPhase.SLOT_SELECTION:
            raise RuntimeError("Cannot select slot: Plan is not awaiting slot selection.")
        if not self.plan.verified_candidate_slots:
            raise RuntimeError("Cannot select slot: No verified candidate slots available.")

        slots = self.plan.verified_candidate_slots
        if choice < 1 or choice > len(slots):
            raise ValueError(
                f"Invalid slot choice '{choice}'. Please choose a number between 1 and {len(slots)}."
            )

        selected = slots[choice - 1]
        participants = self.plan.participants
        date = self.plan.date

        self.log.append({
            "iteration": len(self.log) + 1,
            "planned": "apply user slot selection to existing plan",
            "action": f"user selected slot {choice}: '{selected}'",
            "observed": None,
            "stopped": False,
        })

        self.plan.time_slot = selected
        self.plan.status = "confirmed"
        self.plan.assumptions = [
            f"Verified: All participants ({', '.join(participants)}) are confirmed available for slot {selected} on {date}.",
            "All participants have working hours overlapping the scheduled window.",
            "Timezone UTC+0 applied.",
        ]
        self.plan.next_steps = [
            f"Send calendar invitations to {', '.join(participants)} for {selected} on {date}.",
            "Attach agenda outline and reference links in calendar invite.",
            "Designate minute taker prior to kickoff.",
        ]

        self.goal["plan_generated"] = True
        self.phase = AgentPhase.COMPLETED

        self.log.append({
            "iteration": len(self.log) + 1,
            "planned": "finalize meeting plan with user-selected verified slot",
            "action": f"updated MeetingPlan with confirmed time slot '{selected}'",
            "observed": self.plan.model_dump(),
            "stopped": True,
            "stop_reason": "goal.plan_generated is now True (user-confirmed slot)",
        })

        return self.plan
