"""
Mock Data Store for Calendars and Invitee Preferences
Provides realistic ground-truth data for scheduling, calendars, and preferences.
"""

from typing import Dict, Any, List

MOCK_INVITEES_DB: Dict[str, Dict[str, Any]] = {
    "Alice": {
        "name": "Alice Smith",
        "email": "alice@example.com",
        "role": "Tech Lead",
        "timezone": "UTC+0",
        "working_hours": {"start": "09:00", "end": "17:00"},
        "preferred_times": ["morning", "10:00-12:00"],
        "buffer_minutes": 10,
    },
    "Bob": {
        "name": "Bob Jones",
        "email": "bob@example.com",
        "role": "Senior Software Engineer",
        "timezone": "UTC+0",
        "working_hours": {"start": "09:00", "end": "17:00"},
        "preferred_times": ["afternoon", "14:00-16:00"],
        "buffer_minutes": 15,
    },
    "Charlie": {
        "name": "Charlie Davis",
        "email": "charlie@example.com",
        "role": "Product Manager",
        "timezone": "UTC+0",
        "working_hours": {"start": "09:00", "end": "18:00"},
        "preferred_times": ["morning", "10:00-11:30"],
        "buffer_minutes": 10,
    },
    "Dana": {
        "name": "Dana Miller",
        "email": "dana@example.com",
        "role": "QA Architect",
        "timezone": "UTC+0",
        "working_hours": {"start": "08:30", "end": "16:30"},
        "preferred_times": ["morning", "09:00-12:00"],
        "buffer_minutes": 10,
    },
    "Dr. Meena": {
        "name": "Dr. Meena Rao",
        "email": "meena@example.edu",
        "role": "Faculty / Academic Advisor",
        "timezone": "UTC+0",
        "working_hours": {"start": "10:00", "end": "16:00"},
        "preferred_times": ["afternoon", "13:00-15:00"],
        "buffer_minutes": 15,
    },
}

# Calendar busy intervals per participant per date
MOCK_CALENDARS_DB: Dict[str, Dict[str, List[Dict[str, str]]]] = {
    "Alice": {
        "2026-09-07": [
            {"start": "09:00", "end": "10:00", "title": "Team Standup"},
            {"start": "13:00", "end": "14:00", "title": "Design Sync"},
        ],
        "2026-09-08": [
            {"start": "10:00", "end": "12:00", "title": "Client Meeting"},
            {"start": "15:00", "end": "16:00", "title": "1-on-1"},
        ],
        "Monday": [
            {"start": "09:00", "end": "10:00", "title": "Team Standup"},
            {"start": "13:00", "end": "14:00", "title": "Design Sync"},
        ],
        "Tuesday": [
            {"start": "10:00", "end": "12:00", "title": "Client Meeting"},
            {"start": "15:00", "end": "16:00", "title": "1-on-1"},
        ],
        "Wednesday": [
            {"start": "11:00", "end": "12:30", "title": "Sprint Planning"},
        ],
    },
    "Bob": {
        "2026-09-07": [
            {"start": "11:00", "end": "12:30", "title": "Architecture Sync"},
            {"start": "15:00", "end": "16:00", "title": "Code Review"},
        ],
        "2026-09-08": [
            {"start": "09:00", "end": "10:30", "title": "Dev Sync"},
            {"start": "14:00", "end": "15:30", "title": "Refactoring Session"},
        ],
        "Monday": [
            {"start": "11:00", "end": "12:30", "title": "Architecture Sync"},
            {"start": "15:00", "end": "16:00", "title": "Code Review"},
        ],
        "Tuesday": [
            {"start": "09:00", "end": "10:30", "title": "Dev Sync"},
            {"start": "14:00", "end": "15:30", "title": "Refactoring Session"},
        ],
        "Wednesday": [
            {"start": "14:00", "end": "16:00", "title": "Deep Work"},
        ],
    },
    "Charlie": {
        "2026-09-07": [
            {"start": "09:30", "end": "11:00", "title": "Roadmap Alignment"},
            {"start": "14:00", "end": "15:30", "title": "Customer Discovery"},
        ],
        "Monday": [
            {"start": "09:30", "end": "11:00", "title": "Roadmap Alignment"},
            {"start": "14:00", "end": "15:30", "title": "Customer Discovery"},
        ],
    },
    "Dana": {
        "2026-09-07": [
            {"start": "10:00", "end": "11:30", "title": "Test Automation Review"},
        ],
        "Monday": [
            {"start": "10:00", "end": "11:30", "title": "Test Automation Review"},
        ],
    },
    "Dr. Meena": {
        "2026-09-07": [
            {"start": "10:00", "end": "11:30", "title": "Department Meeting"},
            {"start": "14:00", "end": "15:30", "title": "Office Hours"},
        ],
        "Monday": [
            {"start": "10:00", "end": "11:30", "title": "Department Meeting"},
            {"start": "14:00", "end": "15:30", "title": "Office Hours"},
        ],
    },
}
