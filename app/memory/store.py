"""
Lab 4: Memory & Retrieval - Long-Term Reference Knowledge Store
Stores reference documents, policies, and guidelines, retrievable by tags.
"""

from typing import List, Optional
from app.models.schemas import KnowledgeItem

# Default seeded knowledge items
DEFAULT_KNOWLEDGE_BASE: List[KnowledgeItem] = [
    KnowledgeItem(
        item_id="k-room-01",
        title="Room & AV Resource Booking Policy",
        content="In-person meetings exceeding 4 participants require reserving Room 101 or 202. Video links must be attached for remote participants.",
        tags=["room", "location", "av", "booking", "policy"],
        source="facilities_policy",
    ),
    KnowledgeItem(
        item_id="k-agenda-01",
        title="Standard Committee Agenda Structure",
        content="Committee meetings must include: 1. Opening & Quorum, 2. Carried-over action items, 3. Main discussion, 4. Action item assignment.",
        tags=["agenda", "committee", "structure", "guidelines"],
        source="academic_senate_policy",
    ),
    KnowledgeItem(
        item_id="k-duration-01",
        title="Meeting Duration Guidelines",
        content="Standard meetings are 30 or 45 minutes. Meetings longer than 60 minutes require an explicit break agenda item.",
        tags=["duration", "scheduling", "policy"],
        source="hr_guidelines",
    ),
    KnowledgeItem(
        item_id="k-invitee-01",
        title="Faculty & HoD Preference Rules",
        content="Faculty Advisors prefer afternoon slots between 13:00 and 16:00. HoD prefers morning windows or Tuesdays.",
        tags=["invitees", "preferences", "faculty", "hod"],
        source="faculty_handbook",
    ),
]


class KnowledgeStore:
    """
    Long-term reference knowledge store.
    Stores domain knowledge, policies, and guidelines searchable by tags.
    """

    def __init__(self, initial_items: Optional[List[KnowledgeItem]] = None):
        self._store: List[KnowledgeItem] = list(initial_items or DEFAULT_KNOWLEDGE_BASE)

    def add_item(self, item: KnowledgeItem) -> None:
        """Add a reference document to the knowledge store."""
        self._store.append(item)

    def retrieve_by_tags(self, tags: List[str]) -> List[KnowledgeItem]:
        """
        Retrieve knowledge items matching ANY of the requested tags (case-insensitive).
        Returns all matching items sorted by tag relevance count.
        """
        if not tags:
            return list(self._store)

        query_tags = {t.lower() for t in tags if t}
        results = []

        for item in self._store:
            item_tags = {t.lower() for t in item.tags}
            overlap = len(query_tags.intersection(item_tags))
            if overlap > 0:
                results.append((overlap, item))

        results.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in results]

    def search_text(self, keyword: str) -> List[KnowledgeItem]:
        """Simple keyword text search across title and content."""
        k = keyword.lower()
        return [
            item for item in self._store
            if k in item.title.lower() or k in item.content.lower()
        ]

    def all_items(self) -> List[KnowledgeItem]:
        """Return all items in store."""
        return list(self._store)
