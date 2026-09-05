"""
Scheduling Calculator & Conflict Checker Tool
Calculates common available meeting slots across participants and validates proposed time slots.
Operates deterministically without fabricating availability.
"""

from typing import List, Dict, Any, Tuple
from app.tools.calendar_tool import read_calendar
from app.tools.invitee_tool import read_invitee_preferences


def time_to_minutes(time_str: str) -> int:
    """Convert 'HH:MM' string to minutes from 00:00."""
    parts = time_str.strip().split(":")
    return int(parts[0]) * 60 + int(parts[1])


def minutes_to_time(minutes: int) -> str:
    """Convert minutes from 00:00 to 'HH:MM' format."""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def merge_intervals(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Merge overlapping or contiguous minute intervals."""
    if not intervals:
        return []
    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_intervals[0]]
    for current in sorted_intervals[1:]:
        prev_start, prev_end = merged[-1]
        curr_start, curr_end = current
        if curr_start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, curr_end))
        else:
            merged.append(current)
    return merged


def calculate_meeting_slots(
    participants: List[str],
    date: str,
    duration_minutes: int,
    time_window_start: str = "09:00",
    time_window_end: str = "17:00",
    slot_interval_minutes: int = 30,
) -> Dict[str, Any]:
    """
    Calculate common available meeting slots for a group of participants on a given date.
    
    Args:
        participants: List of participant names (e.g. ['Alice', 'Bob'])
        date: Target date or day (e.g. '2026-09-07' or 'Monday')
        duration_minutes: Required meeting length in minutes
        time_window_start: Default window start (e.g. '09:00')
        time_window_end: Default window end (e.g. '17:00')
        slot_interval_minutes: Step interval for candidate start times
        
    Returns:
        Structured dictionary with available slots, participant work window,
        and busy intervals analyzed.
    """
    if not participants:
        return {"error": "No participants specified for slot calculation"}
    if duration_minutes <= 0:
        return {"error": f"Invalid duration_minutes: {duration_minutes}. Must be > 0"}

    # 1. Determine common working hours window
    window_start_min = time_to_minutes(time_window_start)
    window_end_min = time_to_minutes(time_window_end)
    
    participant_work_hours = {}
    for p in participants:
        pref = read_invitee_preferences(p)
        if "error" in pref:
            return {"error": f"Cannot calculate slots: {pref['error']}"}
        wh = pref["working_hours"]
        p_start = time_to_minutes(wh["start"])
        p_end = time_to_minutes(wh["end"])
        window_start_min = max(window_start_min, p_start)
        window_end_min = min(window_end_min, p_end)
        participant_work_hours[p] = f"{wh['start']}-{wh['end']}"

    if window_start_min + duration_minutes > window_end_min:
        return {
            "date": date,
            "duration_minutes": duration_minutes,
            "checked_participants": participants,
            "available_slots": [],
            "slot_count": 0,
            "note": "No overlapping working hours sufficient for the requested duration",
        }

    # 2. Collect all busy intervals across all participants
    busy_intervals: List[Tuple[int, int]] = []
    participant_busy_details: Dict[str, List[Dict[str, str]]] = {}
    
    for p in participants:
        cal = read_calendar(p, date)
        if "error" in cal:
            return {"error": f"Cannot calculate slots: {cal['error']}"}
        participant_busy_details[p] = cal.get("busy_slots", [])
        for b in cal.get("busy_slots", []):
            b_start = time_to_minutes(b["start"])
            b_end = time_to_minutes(b["end"])
            busy_intervals.append((b_start, b_end))

    merged_busy = merge_intervals(busy_intervals)

    # 3. Find candidate free slots within overlapping working window
    available_slots: List[str] = []
    current_start = window_start_min

    while current_start + duration_minutes <= window_end_min:
        current_end = current_start + duration_minutes
        clash = False
        for b_start, b_end in merged_busy:
            # Overlap condition: max(start1, start2) < min(end1, end2)
            if max(current_start, b_start) < min(current_end, b_end):
                clash = True
                break
        
        if not clash:
            slot_str = f"{minutes_to_time(current_start)}-{minutes_to_time(current_end)}"
            available_slots.append(slot_str)
        
        current_start += slot_interval_minutes

    return {
        "date": date,
        "duration_minutes": duration_minutes,
        "checked_participants": participants,
        "available_slots": available_slots,
        "slot_count": len(available_slots),
        "working_window": f"{minutes_to_time(window_start_min)}-{minutes_to_time(window_end_min)}",
        "merged_busy_intervals": [f"{minutes_to_time(s)}-{minutes_to_time(e)}" for s, e in merged_busy],
    }


def rank_meeting_slots(
    slots: List[str],
    participants: List[str],
) -> List[str]:
    """
    Rank verified available slots by aggregate invitee preference scores.
    Higher-scoring slots (better alignment with preferred_times) appear first.
    """
    if not slots:
        return []

    def slot_start_minutes(slot: str) -> int:
        return time_to_minutes(slot.split("-")[0])

    def slot_end_minutes(slot: str) -> int:
        return time_to_minutes(slot.split("-")[1])

    def preference_score(slot: str, preferred_times: List[str]) -> int:
        start = slot_start_minutes(slot)
        end = slot_end_minutes(slot)
        score = 0
        for pref in preferred_times:
            pref_lower = pref.lower()
            if pref_lower == "morning" and start < 12 * 60:
                score += 1
            elif pref_lower == "afternoon" and start >= 12 * 60:
                score += 1
            elif "-" in pref and ":" in pref:
                try:
                    p_start = time_to_minutes(pref.split("-")[0])
                    p_end = time_to_minutes(pref.split("-")[1])
                    if max(start, p_start) < min(end, p_end):
                        score += 2
                except (ValueError, IndexError):
                    pass
        return score

    scored: List[Tuple[int, int, str]] = []
    for idx, slot in enumerate(slots):
        total = 0
        for p in participants:
            pref = read_invitee_preferences(p)
            if "error" not in pref:
                total += preference_score(slot, pref.get("preferred_times", []))
        scored.append((total, -slot_start_minutes(slot), slot))

    scored.sort(key=lambda x: (-x[0], x[1], x[2]))
    return [slot for _, _, slot in scored]


def validate_slot(
    slot: str,
    participants: List[str],
    date: str,
) -> Dict[str, Any]:
    """
    Validate whether a proposed slot (e.g. '10:00-10:45' or '14:00-15:00') has any conflicts.
    
    Args:
        slot: Slot string 'HH:MM-HH:MM'
        participants: List of participants
        date: Target date or day
        
    Returns:
        Validation report indicating whether slot is valid and any conflicts detected.
    """
    if "-" not in slot:
        return {"error": f"Invalid slot format: '{slot}'. Expected 'HH:MM-HH:MM'"}
    
    parts = slot.split("-")
    try:
        s_min = time_to_minutes(parts[0])
        e_min = time_to_minutes(parts[1])
    except Exception as exc:
        return {"error": f"Error parsing slot times '{slot}': {str(exc)}"}

    if s_min >= e_min:
        return {"error": f"Slot start time must be before end time in '{slot}'"}

    conflicts: List[Dict[str, Any]] = []

    for p in participants:
        # Check working hours
        pref = read_invitee_preferences(p)
        if "error" in pref:
            return {"error": f"Validation failed: {pref['error']}"}
        wh = pref["working_hours"]
        wh_start = time_to_minutes(wh["start"])
        wh_end = time_to_minutes(wh["end"])
        if s_min < wh_start or e_min > wh_end:
            conflicts.append({
                "participant": p,
                "conflict_type": "outside_working_hours",
                "details": f"Working hours are {wh['start']}-{wh['end']}",
            })

        # Check calendar busy events
        cal = read_calendar(p, date)
        if "error" in cal:
            return {"error": f"Validation failed: {cal['error']}"}
        for b in cal.get("busy_slots", []):
            b_start = time_to_minutes(b["start"])
            b_end = time_to_minutes(b["end"])
            if max(s_min, b_start) < min(e_min, b_end):
                conflicts.append({
                    "participant": p,
                    "conflict_type": "calendar_clash",
                    "details": f"Clashes with '{b.get('title', 'Busy')}' ({b['start']}-{b['end']})",
                })

    return {
        "slot": slot,
        "date": date,
        "is_valid": len(conflicts) == 0,
        "conflicts": conflicts,
        "checked_participants": participants,
    }
