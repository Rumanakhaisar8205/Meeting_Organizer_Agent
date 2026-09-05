"""
Integration Tests for FastAPI Endpoints (Lab 1 & Lab 2 Flow)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.session_service import session_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_sessions():
    session_service.clear_all()
    yield
    session_service.clear_all()


def test_root_and_health():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "online"

    resp_health = client.get("/health")
    assert resp_health.status_code == 200
    assert resp_health.json()["status"] == "healthy"


def test_list_tools_endpoint():
    resp = client.get("/api/tools")
    assert resp.status_code == 200
    data = resp.json()
    assert "tools" in data
    assert len(data["tools"]) == 4
    tool_names = [t["name"] for t in data["tools"]]
    assert "read_calendar" in tool_names
    assert "read_invitee_preferences" in tool_names
    assert "calculate_meeting_slots" in tool_names
    assert "validate_slot" in tool_names


def test_start_session_full_request_and_approval_flow():
    # 1. Start full session -> generates draft
    resp = client.post(
        "/api/sessions/start",
        json={"request": "Schedule a 30m architecture sync with Alice and Bob on 2026-09-07"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"].startswith("sess_")
    assert data["current_phase"] == "WAITING_FOR_APPROVAL"
    assert data["plan"] is not None
    assert data["plan"]["duration_minutes"] == 30
    assert "Alice" in data["plan"]["participants"]
    assert "Bob" in data["plan"]["participants"]
    assert "PENDING_VERIFICATION" in data["plan"]["time_slot"]

    session_id = data["session_id"]

    # 2. Approve draft plan -> executes tools and finalizes
    approve_resp = client.post(
        f"/api/sessions/{session_id}/approve",
        json={"approved": True, "notes": "Looks great, proceed with scheduling"},
    )
    assert approve_resp.status_code == 200
    appr_data = approve_resp.json()
    assert appr_data["current_phase"] == "COMPLETED"
    assert appr_data["plan"]["status"] == "confirmed"
    assert "PENDING_VERIFICATION" not in appr_data["plan"]["time_slot"]
    assert len(appr_data["plan"]["verified_candidate_slots"]) > 0


def test_start_session_vague_request_and_clarification_flow():
    # 1. Start with vague request
    resp = client.post(
        "/api/sessions/start",
        json={"request": "Let's meet to discuss the project"},
    )
    assert resp.status_code == 200
    data = resp.json()
    session_id = data["session_id"]
    assert data["current_phase"] == "CLARIFICATION"
    assert data["plan"] is None
    assert len(data["clarification_questions"]) >= 2

    # 2. Provide clarification answers
    clarify_resp = client.post(
        f"/api/sessions/{session_id}/clarify",
        json={
            "answers": {
                "participants": ["Alice", "Bob"],
                "duration_minutes": 45,
                "date_window": "2026-09-07",
            }
        },
    )
    assert clarify_resp.status_code == 200
    c_data = clarify_resp.json()
    assert c_data["current_phase"] == "WAITING_FOR_APPROVAL"
    assert c_data["plan"] is not None
    assert c_data["plan"]["duration_minutes"] == 45


def test_revise_existing_plan_endpoint():
    # 1. Start full session
    resp = client.post(
        "/api/sessions/start",
        json={"request": "Schedule a 30m design sync with Alice and Bob on Monday"},
    )
    session_id = resp.json()["session_id"]

    # 2. Revise plan
    rev_resp = client.post(
        f"/api/sessions/{session_id}/revise",
        json={"feedback": "Make duration 45 mins and add security review to the agenda"},
    )
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()
    assert rev_data["current_phase"] == "WAITING_FOR_APPROVAL"
    assert rev_data["plan"]["duration_minutes"] == 45
    assert rev_data["plan"]["revision_count"] == 1
    assert len(rev_data["revision_history"]) == 1
    assert any("Security" in item["title"] for item in rev_data["plan"]["agenda"])


def test_get_session_trace_endpoint():
    # 1. Start session & approve
    resp = client.post(
        "/api/sessions/start",
        json={"request": "Schedule a 30m sync with Alice and Bob on 2026-09-07"},
    )
    session_id = resp.json()["session_id"]
    client.post(f"/api/sessions/{session_id}/approve", json={"approved": True})

    # 2. Get trace
    trace_resp = client.get(f"/api/sessions/{session_id}/trace")
    assert trace_resp.status_code == 200
    trace_data = trace_resp.json()
    assert "iteration_log" in trace_data
    assert "tool_trace" in trace_data
    assert len(trace_data["iteration_log"]) > 0
    assert len(trace_data["tool_trace"]) > 0
    assert any(t["tool"] == "calculate_meeting_slots" for t in trace_data["tool_trace"])
    assert all(t["success"] is True for t in trace_data["tool_trace"])


def test_session_not_found():
    resp = client.get("/api/sessions/non_existent_session_id")
    assert resp.status_code == 404
