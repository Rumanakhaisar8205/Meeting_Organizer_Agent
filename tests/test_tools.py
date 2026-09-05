"""
Unit Tests for Lab 2: Tools, Centralized Executor, and Error Handling
"""

import pytest
from app.tools.calendar_tool import read_calendar
from app.tools.invitee_tool import read_invitee_preferences
from app.tools.calculator_tool import calculate_meeting_slots, validate_slot
from app.tools.executor import ToolExecutor


def test_read_calendar_valid_and_missing():
    # Valid participant & date
    res = read_calendar("Alice", "2026-09-07")
    assert "error" not in res
    assert res["participant"] == "Alice"
    assert len(res["events"]) == 2
    assert res["count"] == 2

    # Unknown participant
    err_res = read_calendar("NonExistentUser", "2026-09-07")
    assert "error" in err_res
    assert "not found" in err_res["error"]


def test_read_invitee_preferences():
    # Valid invitee
    pref = read_invitee_preferences("Alice")
    assert "error" not in pref
    assert pref["participant"] == "Alice"
    assert pref["working_hours"]["start"] == "09:00"
    assert pref["working_hours"]["end"] == "17:00"

    # Unknown invitee
    err_pref = read_invitee_preferences("NonExistentUser")
    assert "error" in err_pref
    assert "No invitee profile found" in err_pref["error"]


def test_calculate_meeting_slots_no_conflicts():
    # Alice is busy 09:00-10:00, 13:00-14:00 on 2026-09-07
    # Bob is busy 11:00-12:30, 15:00-16:00 on 2026-09-07
    # Common free slots of 30 min within 09:00-17:00:
    # 10:00-10:30, 10:30-11:00, 14:00-14:30, 14:30-15:00, 16:00-16:30, 16:30-17:00
    res = calculate_meeting_slots(
        participants=["Alice", "Bob"],
        date="2026-09-07",
        duration_minutes=30,
    )
    assert "error" not in res
    assert res["slot_count"] > 0
    assert "10:00-10:30" in res["available_slots"]
    assert "14:00-14:30" in res["available_slots"]
    # 09:00-09:30 should NOT be in available slots because Alice is busy
    assert "09:00-09:30" not in res["available_slots"]
    # 11:30-12:00 should NOT be in available slots because Bob is busy
    assert "11:30-12:00" not in res["available_slots"]


def test_validate_slot():
    # Clean slot
    valid_res = validate_slot("10:00-10:30", ["Alice", "Bob"], "2026-09-07")
    assert valid_res["is_valid"] is True
    assert len(valid_res["conflicts"]) == 0

    # Conflicting slot with Alice (busy 09:00-10:00)
    conflict_res = validate_slot("09:15-09:45", ["Alice", "Bob"], "2026-09-07")
    assert conflict_res["is_valid"] is False
    assert len(conflict_res["conflicts"]) > 0
    assert conflict_res["conflicts"][0]["participant"] == "Alice"

    # Outside working hours (Bob works till 17:00)
    late_res = validate_slot("18:00-18:30", ["Alice", "Bob"], "2026-09-07")
    assert late_res["is_valid"] is False
    assert any(c["conflict_type"] == "outside_working_hours" for c in late_res["conflicts"])


def test_centralized_executor_trace_and_error_handling():
    executor = ToolExecutor()
    assert len(executor.get_trace()) == 0

    # Successful call
    res = executor.execute(
        "read_calendar",
        reason="checking Alice's schedule",
        participant="Alice",
        date="2026-09-07",
    )
    assert res["participant"] == "Alice"
    assert len(executor.get_trace()) == 1
    trace_entry = executor.get_trace()[0]
    assert trace_entry["tool"] == "read_calendar"
    assert trace_entry["reason"] == "checking Alice's schedule"
    assert trace_entry["input"]["participant"] == "Alice"
    assert "busy_slots" in trace_entry["output"]

    # Tool error call raises RuntimeError immediately per Lab 2 choke point specification
    with pytest.raises(RuntimeError) as exc_info:
        executor.execute(
            "read_invitee_preferences",
            reason="checking unknown user",
            participant="UnknownGhost",
        )
    assert "read_invitee_preferences failed" in str(exc_info.value)
    assert len(executor.get_trace()) == 2
    assert "error" in executor.get_trace()[1]["output"]

    # Unknown tool raises ValueError
    with pytest.raises(ValueError) as exc_info:
        executor.execute("unregistered_tool", reason="test")
    assert "Unknown tool" in str(exc_info.value)
