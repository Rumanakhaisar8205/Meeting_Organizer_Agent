"""
Interactive Demonstration Script for Meeting Organizer Agent.
Shows a clean user-facing flow and optional debug logs when run with --debug.
"""

import sys
from app.agent.planner import MeetingOrganizerAgent
from app.models.schemas import AgentPhase

DEBUG_MODE = "--debug" in sys.argv


def print_debug_log(agent: MeetingOrganizerAgent):
    """Print full audit log and tool trace only in debug mode."""
    if not DEBUG_MODE:
        return
    print("\n--- DEBUG: AUDIT LOG ---")
    if agent.log:
        for entry in agent.log:
            print(f"Iteration {entry['iteration']}: {entry['planned']}")
            print(f"  Action: {entry['action']}")
            print(f"  Stopped: {entry['stopped']} ({entry.get('stop_reason', 'N/A')})")
            print()

    if agent.executor.trace:
        print("--- DEBUG: TOOL EXECUTION TRACE ---")
        for i, trace in enumerate(agent.executor.trace, 1):
            status = "SUCCESS" if trace.get("success", True) else "FAILED"
            print(f"  {i}. [{status}] {trace['tool']}")
            print(f"     Reason: {trace['reason']}")
            if not trace.get("success", True):
                print(f"     Error: {trace['error']}")
        print()


def format_slot_display(slot: str) -> str:
    """Format '10:00-10:20' as '10:00 - 10:20' for display."""
    if "-" in slot:
        start, end = slot.split("-", 1)
        return f"{start.strip()} - {end.strip()}"
    return slot


def print_draft_plan(draft):
    """Print a draft meeting plan in user-facing format."""
    print(f"\nDraft Meeting Plan")
    print(f"Meeting ID: {draft.meeting_id}")
    print(f"Title: {draft.title}")
    print(f"Purpose: {draft.purpose}")
    print(f"Date: {draft.date}")
    print(f"Duration: {draft.duration_minutes} minutes")
    print(f"Participants: {', '.join(draft.participants)}")
    print(f"Time Slot: {draft.time_slot}")
    print("Agenda:")
    for i, item in enumerate(draft.agenda, 1):
        print(f"  {i}. {item.title} ({item.duration_minutes} min)")
        print(f"     {item.objective}")


def print_final_plan(plan):
    """Print the confirmed meeting plan."""
    print(f"\nFinal Confirmed Meeting Plan")
    print(f"Meeting ID: {plan.meeting_id}")
    print(f"Title: {plan.title}")
    print(f"Purpose: {plan.purpose}")
    print(f"Date: {plan.date}")
    print(f"Duration: {plan.duration_minutes} minutes")
    print(f"Confirmed Time Slot: {plan.time_slot}")
    print(f"Status: {plan.status}")
    print(f"Participants: {', '.join(plan.participants)}")
    print("Agenda:")
    for i, item in enumerate(plan.agenda, 1):
        print(f"  {i}. {item.title} ({item.duration_minutes} min)")


def collect_clarification_answer(field: str, question: str) -> str:
    """Prompt the user for a single missing field."""
    while True:
        value = input(f"{question}\n> ").strip()
        if not value:
            print("Please provide a value.")
            continue
        if field == "duration_minutes":
            try:
                return int(value)
            except ValueError:
                print("Invalid duration. Please enter a number of minutes.")
                continue
        return value


def run_interactive_mode():
    """Run the complete Lab 1 and Lab 2 flow."""
    agent = MeetingOrganizerAgent()

    print("Describe your meeting request.")
    print()
    print("Example:")
    print('"Schedule a meeting with Alice and Bob to discuss project planning next Monday for 60 minutes"')
    print()
    user_request = input("Your request:\n> ").strip()
    if not user_request:
        print("Please provide a meeting request.")
        return

    print(f"\nYour request: {user_request}")
    agent.extract_from_text(user_request)

    # Clarification loop — ask only for genuinely missing information
    field_order = ("topic", "participants", "duration_minutes", "date_window")
    while True:
        missing = agent.latest_analysis.missing_fields if agent.latest_analysis else []
        if not missing:
            break

        questions = agent.get_missing_clarification_questions()
        answers = {}
        for i, field in enumerate(missing):
            question = questions[i] if i < len(questions) else f"Please provide {field.replace('_', ' ')}:"
            if field == "participants":
                answers[field] = collect_clarification_answer(field, question)
            else:
                answers[field] = collect_clarification_answer(field, question)

        agent.apply_clarification(answers)

    # Generate draft
    draft = agent.run()
    if not draft:
        print("Could not generate draft plan.")
        return

    print_draft_plan(draft)

    # Approval and revision loop
    while agent.phase == AgentPhase.WAITING_FOR_APPROVAL:
        print("\nChoose an action:")
        print("[a] Approve and continue to scheduling")
        print("[r] Request changes")
        choice = input("> ").strip().lower()

        if choice == "r":
            feedback = input("What changes would you like?\n> ").strip()
            if not feedback:
                print("Please describe the changes you want, or choose [a] to approve.")
                continue
            revised = agent.revise(feedback)
            print_draft_plan(revised)
            continue

        if choice == "a":
            break

        print("Invalid choice. Please enter [a] to approve or [r] to request changes.")

    # Lab 2 — only after explicit approval
    print("\nScheduling: checking invitee preferences and calendar availability...")
    plan = agent.approve_draft()

    if agent.phase == AgentPhase.SLOT_SELECTION and plan.verified_candidate_slots:
        print("\nAvailable time slots (ranked by invitee preferences):")
        for i, slot in enumerate(plan.verified_candidate_slots, 1):
            print(f"{i}. {format_slot_display(slot)}")

        k = len(plan.verified_candidate_slots)
        while True:
            slot_choice = input(f"\nChoose your preferred slot [1-{k}]:\n> ").strip()
            try:
                choice_num = int(slot_choice)
                final_plan = agent.select_time_slot(choice_num)
                break
            except ValueError as exc:
                print(str(exc))
            except Exception:
                print(f"Invalid choice. Please enter a number between 1 and {k}.")

        print_final_plan(final_plan)
    elif plan.status == "unresolved_conflict":
        print("\nNo common available slots were found for all participants.")
        print(f"Meeting ID: {plan.meeting_id}")
        print(f"Status: {plan.status}")
    else:
        print_final_plan(plan)

    print_debug_log(agent)


if __name__ == "__main__":
    try:
        run_interactive_mode()
    except KeyboardInterrupt:
        print("\nSession interrupted.")
        sys.exit(0)
    except Exception as e:
        if DEBUG_MODE:
            import traceback
            traceback.print_exc()
        else:
            print(f"\nAn error occurred: {e}")
        sys.exit(1)
