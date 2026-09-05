"""
Calendar Tool
Reads calendar busy intervals and scheduled events for participants from mock data.
Follows strict structured tool contracts with explicit error reporting.
"""

from typing import Dict, Any
from app.data.mock_data import MOCK_CALENDARS_DB


def read_calendar(participant: str, date: str) -> Dict[str, Any]:
    """
    Read scheduled events and busy intervals for a given participant and date.
    
    Args:
        participant: Name of the participant (e.g., 'Alice')
        date: Target date or day string (e.g., '2026-09-07' or 'Monday')
        
    Returns:
        Structured dictionary with events, busy_slots, and count,
        or an explicit error dictionary if the participant is unknown.
    """
    # Normalize participant lookup (case-insensitive)
    found_key = next((k for k in MOCK_CALENDARS_DB if k.lower() == participant.strip().lower()), None)
    if not found_key:
        return {"error": f"Calendar not found for participant '{participant}'"}
    
    user_cal = MOCK_CALENDARS_DB[found_key]
    # Check exact date or day key
    events = user_cal.get(date, [])
    
    busy_slots = [{"start": e["start"], "end": e["end"], "title": e.get("title", "Busy")} for e in events]
    
    return {
        "participant": found_key,
        "date": date,
        "events": events,
        "busy_slots": busy_slots,
        "count": len(events),
    }
