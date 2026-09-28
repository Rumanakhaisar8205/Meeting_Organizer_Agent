"""
FastAPI Routes for Meeting Organizer Agent
Provides REST API endpoints for starting sessions, clarifying details,
approving draft plans, revising plans, and inspecting execution traces.
"""

from fastapi import APIRouter, HTTPException, Path
from typing import Dict, Any, Optional

from app.models.schemas import (
    StartSessionRequest,
    ClarificationRequest,
    RevisionRequest,
    ApprovePlanRequest,
    SelectSlotRequest,
    SessionStateResponse,
    SessionTraceResponse,
    PlanSkillInput,
    LockedPlanBlueprint,
    FormatSkillInput,
    FormattedDocumentResponse,
    MemoryQueryRequest,
    MemorySearchResponse,
    HistoryRecordRequest,
    MeetingHistoryRecord,
    ActionItemTemplate,
)
from app.services.session_service import session_service
from app.tools.executor import TOOLS
from app.data.mock_data import MOCK_INVITEES_DB, MOCK_CALENDARS_DB
from app.skills.plan_skill import PlanSkill
from app.skills.format_skill import FormatSkill
from app.memory.store import KnowledgeStore
from app.memory.history import MeetingHistoryStore

router = APIRouter(prefix="/api", tags=["Meeting Organizer"])

# Shared global store instances for stand-alone API endpoints
global_knowledge_store = KnowledgeStore()
global_history_store = MeetingHistoryStore()
global_plan_skill = PlanSkill()
global_format_skill = FormatSkill()


@router.post(
    "/sessions/start",
    response_model=SessionStateResponse,
    summary="Start a meeting planning session",
    description="Accepts a free-text request, extracts known parameters through deterministic rule-based analysis, asks for missing requirements, or generates the initial draft plan.",
)
def start_session(payload: StartSessionRequest) -> SessionStateResponse:
    return session_service.create_session(request_text=payload.request)


@router.post(
    "/sessions/{session_id}/clarify",
    response_model=SessionStateResponse,
    summary="Provide clarification answers",
    description="Fills in missing goal requirements and resumes the planning loop toward draft plan generation.",
)
def clarify_session(
    session_id: str = Path(..., description="Session identifier"),
    payload: ClarificationRequest = ...,
) -> SessionStateResponse:
    try:
        return session_service.clarify_session(session_id=session_id, answers=payload.answers)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/sessions/{session_id}/revise",
    response_model=SessionStateResponse,
    summary="Revise an existing draft meeting plan",
    description="Mutates the existing draft meeting plan in-place based on user feedback without restarting the loop. Preserves unchanged fields.",
)
def revise_session(
    session_id: str = Path(..., description="Session identifier"),
    payload: RevisionRequest = ...,
) -> SessionStateResponse:
    try:
        return session_service.revise_session(session_id=session_id, feedback=payload.feedback)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/sessions/{session_id}/approve",
    response_model=SessionStateResponse,
    summary="Approve draft plan and trigger Lab 2 Tool Execution",
    description="Explicit human approval gate: transitions session to TOOL_EXECUTION, calls preferences/calendars/calculator tools, and finalizes meeting plan.",
)
def approve_session(
    session_id: str = Path(..., description="Session identifier"),
    payload: Optional[ApprovePlanRequest] = None,
) -> SessionStateResponse:
    try:
        notes = payload.notes if payload else None
        approved = payload.approved if payload is not None else True
        return session_service.approve_session(session_id=session_id, notes=notes, approved=approved)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/sessions/{session_id}/select-slot",
    response_model=SessionStateResponse,
    summary="Select a verified Top-K time slot and confirm the plan",
    description="Applies the user's choice from the ranked verified_candidate_slots, marking the existing MeetingPlan as confirmed.",
)
def select_slot(
    session_id: str = Path(..., description="Session identifier"),
    payload: SelectSlotRequest = ...,
) -> SessionStateResponse:
    try:
        return session_service.select_slot(session_id=session_id, choice=payload.choice)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/sessions/{session_id}",
    response_model=SessionStateResponse,
    summary="Get current session state & plan",
    description="Retrieves the current phase, goal predicate, missing fields, revision history, and plan.",
)
def get_session_state(
    session_id: str = Path(..., description="Session identifier")
) -> SessionStateResponse:
    try:
        return session_service.get_session(session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/sessions/{session_id}/trace",
    response_model=SessionTraceResponse,
    summary="Get iteration log and tool execution trace",
    description="Returns the full Goal-Plan-Act-Observe iteration log and the centralized tool execution trace for auditing.",
)
def get_session_trace(
    session_id: str = Path(..., description="Session identifier")
) -> SessionTraceResponse:
    try:
        return session_service.get_session_trace(session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---- Lab 3: Skill Creation Routes ----------------------------------------
@router.post(
    "/skills/plan",
    response_model=LockedPlanBlueprint,
    summary="Lab 3: Execute PlanSkill to generate a locked meeting blueprint",
    description="Invokes the reusable, schema-typed PlanSkill to produce a locked blueprint for any meeting type.",
)
def execute_plan_skill(payload: PlanSkillInput) -> LockedPlanBlueprint:
    return global_plan_skill.execute(payload)


@router.post(
    "/skills/format",
    response_model=FormattedDocumentResponse,
    summary="Lab 3: Execute FormatSkill to format a MeetingPlan",
    description="Invokes the reusable FormatSkill to render a MeetingPlan into Markdown, Plain Text, or HTML documents.",
)
def execute_format_skill(payload: FormatSkillInput) -> FormattedDocumentResponse:
    return global_format_skill.execute(payload)


@router.post(
    "/sessions/{session_id}/format",
    response_model=FormattedDocumentResponse,
    summary="Lab 3: Format the active session's MeetingPlan",
    description="Renders the current draft/confirmed meeting plan of a session using FormatSkill.",
)
def format_session_plan(
    session_id: str = Path(..., description="Session identifier"),
    template_format: str = "markdown",
) -> FormattedDocumentResponse:
    try:
        session = session_service.get_session_agent(session_id)
        return session.format_plan(template_format=template_format)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---- Lab 4: Memory & Retrieval Routes -----------------------------------
@router.post(
    "/memory/search",
    response_model=MemorySearchResponse,
    summary="Lab 4: Search knowledge store and meeting history",
    description="Retrieves tagged reference rules from KnowledgeStore and TF-IDF similar meeting records from MeetingHistoryStore.",
)
def search_memory(payload: MemoryQueryRequest) -> MemorySearchResponse:
    k_hits = global_knowledge_store.retrieve_by_tags(payload.tags) if payload.tags else []
    h_hits = (
        global_history_store.retrieve_similar(payload.query_text, top_k=payload.top_k)
        if payload.query_text
        else global_history_store.all_records()[: payload.top_k]
    )
    return MemorySearchResponse(knowledge_hits=k_hits, history_hits=h_hits)


@router.post(
    "/memory/history/add",
    response_model=MeetingHistoryRecord,
    summary="Lab 4: Seed or archive a meeting into MeetingHistoryStore",
    description="Adds a historical meeting record containing decisions and open action items into the long-term archive.",
)
def add_history_record(payload: HistoryRecordRequest) -> MeetingHistoryRecord:
    import uuid
    record = MeetingHistoryRecord(
        meeting_id=f"hist-{uuid.uuid4().hex[:6]}",
        title=payload.title,
        date=payload.date,
        participants=payload.participants,
        summary=payload.summary,
        decisions=payload.decisions,
        open_action_items=payload.open_action_items,
        tags=payload.tags,
    )
    global_history_store.add_record(record)
    return record


@router.get(
    "/tools",
    summary="List available tools and schemas",
    description="Returns registered tools and mock database summaries.",
)
def list_tools() -> Dict[str, Any]:
    return {
        "tools": [
            {
                "name": "read_calendar",
                "description": "Reads busy intervals and booked events for a participant and date.",
                "input": {"participant": "str", "date": "str"},
                "output": {"participant": "str", "date": "str", "events": "list", "busy_slots": "list", "count": "int"},
            },
            {
                "name": "read_invitee_preferences",
                "description": "Retrieves working hours, role, timezone, and meeting preferences for a participant.",
                "input": {"participant": "str"},
                "output": {"participant": "str", "profile": "dict", "working_hours": "dict", "preferred_times": "list", "timezone": "str"},
            },
            {
                "name": "calculate_meeting_slots",
                "description": "Calculates mutually available collision-free continuous time slots using ground-truth data.",
                "input": {"participants": "list[str]", "date": "str", "duration_minutes": "int", "time_window_start": "str", "time_window_end": "str"},
                "output": {"date": "str", "duration_minutes": "int", "available_slots": "list[str]", "slot_count": "int"},
            },
            {
                "name": "validate_slot",
                "description": "Validates whether a proposed slot has any calendar clashes or working-hour violations.",
                "input": {"slot": "str", "participants": "list[str]", "date": "str"},
                "output": {"slot": "str", "date": "str", "is_valid": "bool", "conflicts": "list"},
            },
        ],
        "skills": ["PlanSkill", "FormatSkill"],
        "memory_stores": ["ShortTermSessionState", "KnowledgeStore", "MeetingHistoryStore"],
        "registered_invitees": list(MOCK_INVITEES_DB.keys()),
        "registered_calendars": list(MOCK_CALENDARS_DB.keys()),
    }



@router.post(
    "/sessions/start",
    response_model=SessionStateResponse,
    summary="Start a meeting planning session",
    description="Accepts a free-text request, extracts known parameters through deterministic rule-based analysis, asks for missing requirements, or generates the initial draft plan.",
)
def start_session(payload: StartSessionRequest) -> SessionStateResponse:
    return session_service.create_session(request_text=payload.request)


@router.post(
    "/sessions/{session_id}/clarify",
    response_model=SessionStateResponse,
    summary="Provide clarification answers",
    description="Fills in missing goal requirements and resumes the planning loop toward draft plan generation.",
)
def clarify_session(
    session_id: str = Path(..., description="Session identifier"),
    payload: ClarificationRequest = ...,
) -> SessionStateResponse:
    try:
        return session_service.clarify_session(session_id=session_id, answers=payload.answers)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/sessions/{session_id}/revise",
    response_model=SessionStateResponse,
    summary="Revise an existing draft meeting plan",
    description="Mutates the existing draft meeting plan in-place based on user feedback without restarting the loop. Preserves unchanged fields.",
)
def revise_session(
    session_id: str = Path(..., description="Session identifier"),
    payload: RevisionRequest = ...,
) -> SessionStateResponse:
    try:
        return session_service.revise_session(session_id=session_id, feedback=payload.feedback)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/sessions/{session_id}/approve",
    response_model=SessionStateResponse,
    summary="Approve draft plan and trigger Lab 2 Tool Execution",
    description="Explicit human approval gate: transitions session to TOOL_EXECUTION, calls preferences/calendars/calculator tools, and finalizes meeting plan.",
)
def approve_session(
    session_id: str = Path(..., description="Session identifier"),
    payload: Optional[ApprovePlanRequest] = None,
) -> SessionStateResponse:
    try:
        notes = payload.notes if payload else None
        approved = payload.approved if payload is not None else True
        return session_service.approve_session(session_id=session_id, notes=notes, approved=approved)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/sessions/{session_id}/select-slot",
    response_model=SessionStateResponse,
    summary="Select a verified Top-K time slot and confirm the plan",
    description="Applies the user's choice from the ranked verified_candidate_slots, marking the existing MeetingPlan as confirmed.",
)
def select_slot(
    session_id: str = Path(..., description="Session identifier"),
    payload: SelectSlotRequest = ...,
) -> SessionStateResponse:
    try:
        return session_service.select_slot(session_id=session_id, choice=payload.choice)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/sessions/{session_id}",
    response_model=SessionStateResponse,
    summary="Get current session state & plan",
    description="Retrieves the current phase, goal predicate, missing fields, revision history, and plan.",
)
def get_session_state(
    session_id: str = Path(..., description="Session identifier")
) -> SessionStateResponse:
    try:
        return session_service.get_session(session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/sessions/{session_id}/trace",
    response_model=SessionTraceResponse,
    summary="Get iteration log and tool execution trace",
    description="Returns the full Goal-Plan-Act-Observe iteration log and the centralized tool execution trace for auditing.",
)
def get_session_trace(
    session_id: str = Path(..., description="Session identifier")
) -> SessionTraceResponse:
    try:
        return session_service.get_session_trace(session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/tools",
    summary="List available tools and schemas",
    description="Returns registered tools and mock database summaries.",
)
def list_tools() -> Dict[str, Any]:
    return {
        "tools": [
            {
                "name": "read_calendar",
                "description": "Reads busy intervals and booked events for a participant and date.",
                "input": {"participant": "str", "date": "str"},
                "output": {"participant": "str", "date": "str", "events": "list", "busy_slots": "list", "count": "int"},
            },
            {
                "name": "read_invitee_preferences",
                "description": "Retrieves working hours, role, timezone, and meeting preferences for a participant.",
                "input": {"participant": "str"},
                "output": {"participant": "str", "profile": "dict", "working_hours": "dict", "preferred_times": "list", "timezone": "str"},
            },
            {
                "name": "calculate_meeting_slots",
                "description": "Calculates mutually available collision-free continuous time slots using ground-truth data.",
                "input": {"participants": "list[str]", "date": "str", "duration_minutes": "int", "time_window_start": "str", "time_window_end": "str"},
                "output": {"date": "str", "duration_minutes": "int", "available_slots": "list[str]", "slot_count": "int"},
            },
            {
                "name": "validate_slot",
                "description": "Validates whether a proposed slot has any calendar clashes or working-hour violations.",
                "input": {"slot": "str", "participants": "list[str]", "date": "str"},
                "output": {"slot": "str", "date": "str", "is_valid": "bool", "conflicts": "list"},
            },
        ],
        "registered_invitees": list(MOCK_INVITEES_DB.keys()),
        "registered_calendars": list(MOCK_CALENDARS_DB.keys()),
    }