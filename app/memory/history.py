"""
Lab 4: Memory & Retrieval - Meeting History Archive Store
Stores prior meeting history, decisions, and action items.
Supports term-similarity retrieval and open action item carryover.
"""

import math
import re
from typing import List, Dict, Set
from app.models.schemas import MeetingHistoryRecord, ActionItemTemplate

# Default seeded history records representing prior meetings
DEFAULT_HISTORY_RECORDS: List[MeetingHistoryRecord] = [
    MeetingHistoryRecord(
        meeting_id="hist-001",
        title="Project Planning & Exam Guidelines Kickoff",
        date="2026-08-20",
        participants=["Alice", "Bob", "Dr. Meena"],
        summary="Initial alignment on upcoming exam format and project milestone scheduling.",
        decisions=[
            "Agreed to hold exams online using LMS portal",
            "Set project submission deadline for Sept 15",
        ],
        open_action_items=[
            ActionItemTemplate(
                description="Draft preliminary exam question bank and rubric",
                owner="Alice",
                deadline="2026-09-01",
            ),
            ActionItemTemplate(
                description="Review LMS platform capacity with IT department",
                owner="Bob",
                deadline="2026-09-05",
            ),
        ],
        tags=["exam", "planning", "rubric", "lms", "project"],
    ),
    MeetingHistoryRecord(
        meeting_id="hist-002",
        title="Committee Review on Curriculum Revisions",
        date="2026-08-25",
        participants=["Faculty Advisor", "HoD", "Committee Member A"],
        summary="Discussion on syllabus updates and student feedback collection.",
        decisions=[
            "Approved 3 credit hour adjustment for Lab courses",
        ],
        open_action_items=[
            ActionItemTemplate(
                description="Prepare updated course catalog draft for HoD approval",
                owner="Committee Member A",
                deadline="2026-09-10",
            ),
        ],
        tags=["committee", "curriculum", "syllabus", "hod"],
    ),
    MeetingHistoryRecord(
        meeting_id="hist-003",
        title="Sprint Planning & Architecture Sync",
        date="2026-08-28",
        participants=["Alice", "Bob", "Charlie"],
        summary="Sprint planning meeting for agent backend framework integration.",
        decisions=[
            "Adopted FastAPI with Pydantic schemas",
        ],
        open_action_items=[
            ActionItemTemplate(
                description="Implement mock calendar and preference reader tools",
                owner="Bob",
                deadline="2026-09-02",
            ),
        ],
        tags=["sprint", "architecture", "fastapi", "agent"],
    ),
]


def tokenize(text: str) -> List[str]:
    """Simple alphanumeric tokenizer for text indexing."""
    return re.findall(r"\w+", text.lower())


class MeetingHistoryStore:
    """
    Long-term archive for prior meetings.
    Supports similarity search (TF-IDF term overlap) and action item retrieval.
    """

    def __init__(self, initial_records: List[MeetingHistoryRecord] = None):
        self._records: List[MeetingHistoryRecord] = list(initial_records or DEFAULT_HISTORY_RECORDS)

    def add_record(self, record: MeetingHistoryRecord) -> None:
        """Add a meeting record to history."""
        self._records.append(record)

    def retrieve_similar(self, query_text: str, top_k: int = 5) -> List[MeetingHistoryRecord]:
        """
        Retrieve prior meeting records ranked by similarity to query_text.
        Uses TF-IDF term overlap score.
        """
        if not query_text or not self._records:
            return self._records[:top_k]

        query_tokens = set(tokenize(query_text))
        if not query_tokens:
            return self._records[:top_k]

        # Calculate document frequencies
        doc_count = len(self._records)
        doc_freq: Dict[str, int] = {}
        for rec in self._records:
            rec_text = f"{rec.title} {rec.summary} {' '.join(rec.decisions)} {' '.join(rec.tags)}"
            tokens = set(tokenize(rec_text))
            for t in tokens:
                doc_freq[t] = doc_freq.get(t, 0) + 1

        STOP_WORDS = {"meeting", "sync", "review", "schedule", "with", "and", "for", "on", "the", "in", "to", "a", "an", "is", "of"}
        filtered_query_tokens = {t for t in query_tokens if t not in STOP_WORDS and len(t) > 1}
        tokens_to_match = filtered_query_tokens if filtered_query_tokens else query_tokens

        scores = []
        for rec in self._records:
            rec_text = f"{rec.title} {rec.summary} {' '.join(rec.decisions)} {' '.join(rec.tags)}"
            rec_tokens = tokenize(rec_text)

            score = 0.0
            for t in tokens_to_match:
                if t in rec_tokens:
                    tf = rec_tokens.count(t) / max(1, len(rec_tokens))
                    idf = math.log((1 + doc_count) / (1 + doc_freq.get(t, 0))) + 1.0
                    score += tf * idf

            if score > 0:
                scores.append((score, rec))

        # Sort by similarity score descending
        scores.sort(key=lambda x: x[0], reverse=True)

        if not scores:
            return []

        return [rec for _, rec in scores[:top_k]]

    def get_open_action_items_for_topic(self, topic: str) -> List[ActionItemTemplate]:
        """
        Extract open action items from prior meetings relevant to the given topic.
        """
        similar_records = self.retrieve_similar(topic, top_k=3)
        action_items = []
        seen_descriptions = set()

        for rec in similar_records:
            for ai in rec.open_action_items:
                if ai.description not in seen_descriptions:
                    action_items.append(ai)
                    seen_descriptions.add(ai.description)

        return action_items

    def all_records(self) -> List[MeetingHistoryRecord]:
        """Return all historical records."""
        return list(self._records)
