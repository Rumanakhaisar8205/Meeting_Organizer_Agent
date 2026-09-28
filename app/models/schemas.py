from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentPhase(str, Enum):
    CLARIFICATION = "CLARIFICATION"
    DRAFT_GENERATION = "DRAFT_GENERATION"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    REVISION = "REVISION"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    SLOT_SELECTION = "SLOT_SELECTION"
    COMPLETED = "COMPLETED"


class AgendaItem(BaseModel):
    title: str
    duration_minutes: int
    objective: str


class ActionItemTemplate(BaseModel):
    description: str
    owner: str
    deadline: str


class MinutesOutline(BaseModel):
    discussion_topics: List[str] = Field(default_factory=list)
    key_decisions: List[str] = Field(default_factory=list)
    action_items: List[ActionItemTemplate] = Field(default_factory=list)


class RevisionHistoryEntry(BaseModel):
    revision_number: int
    feedback: str
    mutations: List[str]
    timestamp: str


class MeetingPlan(BaseModel):
    meeting_id: str
    title: str
    purpose: str
    date: str
    time_slot: str = "PENDING_VERIFICATION"
    verified_candidate_slots: List[str] = Field(default_factory=list)
    duration_minutes: int
    participants: List[str]
    agenda: List[AgendaItem]
    minutes_outline: MinutesOutline
    assumptions: List[str]
    next_steps: List[str]
    status: str = "draft"  # "draft", "waiting_for_approval", "revised", "confirmed"
    revision_count: int = 0
    revision_history: List[RevisionHistoryEntry] = Field(default_factory=list)


class IterationLogEntry(BaseModel):
    iteration: int
    planned: str
    action: str
    observed: Any = None
    stopped: bool = False
    stop_reason: Optional[str] = None


class ToolTraceEntry(BaseModel):
    tool: str
    reason: str
    input: Dict[str, Any]
    output: Dict[str, Any]
    success: bool = True
    error: Optional[str] = None


class StartSessionRequest(BaseModel):
    request: str = Field(
        ...,
        description="Free-text meeting request e.g., 'Schedule a 30m sprint sync with Alice and Bob on Monday'",
        examples=["Schedule a 45m architecture review with Alice and Bob on 2026-09-07"],
    )


class ClarificationRequest(BaseModel):
    answers: Dict[str, Any] = Field(
        ...,
        description="Dictionary providing missing fields e.g., {'duration_minutes': 30, 'date_window': '2026-09-07'}",
        examples=[{"duration_minutes": 30, "date_window": "2026-09-07"}],
    )


class RevisionRequest(BaseModel):
    feedback: str = Field(
        ...,
        description="User feedback to mutate the plan e.g., 'Move meeting to 14:00 and add security review to agenda'",
        examples=["Move meeting to afternoon and add Charlie to participants"],
    )


class ApprovePlanRequest(BaseModel):
    approved: bool = Field(default=True, description="Whether the user explicitly approves the draft plan")
    notes: Optional[str] = Field(default=None, description="Optional approval notes or constraints")


class SelectSlotRequest(BaseModel):
    choice: int = Field(
        ...,
        ge=1,
        description="1-based index into the Top-K verified_candidate_slots to confirm",
        examples=[1],
    )


class SessionStateResponse(BaseModel):
    session_id: str
    current_phase: AgentPhase
    status: str
    goal: Dict[str, Any]
    missing_fields: List[str]
    clarification_questions: List[str]
    plan: Optional[MeetingPlan] = None
    revision_history: List[RevisionHistoryEntry] = Field(default_factory=list)
    iterations_count: int
    tool_calls_count: int


class SessionTraceResponse(BaseModel):
    session_id: str
    current_phase: AgentPhase
    iteration_log: List[IterationLogEntry]
    tool_trace: List[ToolTraceEntry]


# ---- Lab 3: Skill Creation Schemas --------------------------------------
class PlanSkillInput(BaseModel):
    topic: str
    duration_minutes: int = 30
    participants: List[str]
    date_window: str = "2026-09-07"
    meeting_type: str = "general"  # "committee", "standup", "sprint_planning", "project_sync", "general"
    prior_action_items: List[ActionItemTemplate] = Field(default_factory=list)
    notes: Optional[str] = None


class LockedPlanBlueprint(BaseModel):
    blueprint_id: str
    topic: str
    meeting_type: str
    participants: List[str]
    duration_minutes: int
    date_window: str
    agenda_structure: List[AgendaItem]
    minutes_template: MinutesOutline
    constraints_locked: bool = True


class FormatSkillInput(BaseModel):
    plan: MeetingPlan
    template_format: str = "markdown"  # "markdown", "text", "html"
    include_minutes_template: bool = True


class FormattedDocumentResponse(BaseModel):
    format_type: str
    content: str
    sections: Dict[str, str] = Field(default_factory=dict)


# ---- Lab 4: Memory & Retrieval Schemas -----------------------------------
class KnowledgeItem(BaseModel):
    item_id: str
    title: str
    content: str
    tags: List[str]
    source: str = "knowledge_store"


class MeetingHistoryRecord(BaseModel):
    meeting_id: str
    title: str
    date: str
    participants: List[str]
    summary: str
    decisions: List[str] = Field(default_factory=list)
    open_action_items: List[ActionItemTemplate] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class MemoryQueryRequest(BaseModel):
    tags: List[str] = Field(default_factory=list)
    query_text: Optional[str] = None
    top_k: int = 5


class MemorySearchResponse(BaseModel):
    knowledge_hits: List[KnowledgeItem] = Field(default_factory=list)
    history_hits: List[MeetingHistoryRecord] = Field(default_factory=list)


class HistoryRecordRequest(BaseModel):
    title: str
    date: str
    participants: List[str]
    summary: str
    decisions: List[str] = Field(default_factory=list)
    open_action_items: List[ActionItemTemplate] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)