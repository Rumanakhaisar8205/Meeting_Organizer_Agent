"""
Invitee Preferences Tool
Reads participant profiles, working hours, timezones, and scheduling preferences.
"""

from typing import Dict, Any
from app.data.mock_data import MOCK_INVITEES_DB


def read_invitee_preferences(participant: str) -> Dict[str, Any]:
    """
    Retrieve working hours, role, timezone, and meeting preferences for a participant.
    
    Args:
        participant: Name of the participant (e.g., 'Alice')
        
    Returns:
        Structured dictionary with participant profile,
        or an explicit error dictionary if participant is not found.
    """
    found_key = next((k for k in MOCK_INVITEES_DB if k.lower() == participant.strip().lower()), None)
    if not found_key:
        return {"error": f"No invitee profile found for '{participant}'"}
    
    profile = MOCK_INVITEES_DB[found_key]
    return {
        "participant": found_key,
        "profile": profile,
        "working_hours": profile.get("working_hours", {"start": "09:00", "end": "17:00"}),
        "preferred_times": profile.get("preferred_times", []),
        "timezone": profile.get("timezone", "UTC+0"),
    }
