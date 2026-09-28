"""
Tests for Lab 4: Memory & Retrieval
Verifies short-term session state separation, long-term KnowledgeStore tag retrieval,
MeetingHistoryStore similarity retrieval, and action item carryover.
"""

import pytest
from app.memory.session_state import ShortTermSessionState
from app.memory.store import KnowledgeStore
from app.memory.history import MeetingHistoryStore
from app.models.schemas import (
    MeetingPlan,
    AgendaItem,
    MinutesOutline,
    KnowledgeItem,
    MeetingHistoryRecord,
    ActionItemTemplate,
)


def test_short_term_session_state_isolation():
    """Verify ShortTermSessionState tracks active drafts and iterations in isolation."""
    session = ShortTermSessionState(session_id="test-session-123")
    assert session.draft_plan is None
    assert len(session.candidate_history) == 0

    plan1 = MeetingPlan(
        meeting_id="m1",
        title="Draft 1",
        purpose="Testing",
        date="2026-09-07",
        duration_minutes=30,
        participants=["Alice"],
        agenda=[],
        minutes_outline=MinutesOutline(),
        assumptions=[],
        next_steps=[],
    )
    session.set_draft(plan1)

    assert session.get_latest_candidate() == plan1
    assert len(session.candidate_history) == 1

    session.clear()
    assert session.draft_plan is None
    assert len(session.candidate_history) == 0


def test_knowledge_store_tag_retrieval():
    """Verify KnowledgeStore tag-based retrieval."""
    store = KnowledgeStore()

    # Search for room & location policies
    hits = store.retrieve_by_tags(["room", "booking"])
    assert len(hits) > 0
    assert any("Room" in item.title for item in hits)

    # Search for non-existent tag
    empty_hits = store.retrieve_by_tags(["nonexistent_tag_xyz"])
    assert len(empty_hits) == 0


def test_meeting_history_store_similarity_retrieval():
    """Verify MeetingHistoryStore similarity search and action item carryover."""
    history = MeetingHistoryStore()

    # Similarity search for "exam review"
    similar = history.retrieve_similar("exam guidelines and rubric", top_k=2)
    assert len(similar) > 0
    assert "Exam" in similar[0].title or "exam" in similar[0].tags

    # Open action item carryover for exam topic
    open_actions = history.get_open_action_items_for_topic("exam")
    assert len(open_actions) > 0
    assert any("exam" in ai.description.lower() or "rubric" in ai.description.lower() for ai in open_actions)


def test_custom_history_record_addition():
    """Verify adding custom history records to archive."""
    history = MeetingHistoryStore(initial_records=[])
    rec = MeetingHistoryRecord(
        meeting_id="h-custom",
        title="Custom Architecture Sync",
        date="2026-09-01",
        participants=["Alice", "Bob"],
        summary="Discussed microservice integration.",
        decisions=["Adopted gRPC"],
        open_action_items=[
            ActionItemTemplate(description="Benchmark gRPC latency", owner="Bob", deadline="2026-09-10")
        ],
        tags=["architecture", "grpc"],
    )
    history.add_record(rec)

    results = history.retrieve_similar("grpc microservice", top_k=1)
    assert len(results) == 1
    assert results[0].meeting_id == "h-custom"
