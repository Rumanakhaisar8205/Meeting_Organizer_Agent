# Meeting Organizer Agent

## Project Overview

Meeting Organizer Agent is a Python meeting-scheduling application that demonstrates an agent-based **Goal -> Plan -> Act -> Observe -> Revise** workflow. It accepts a natural-language meeting request, gathers any missing details, prepares a draft `MeetingPlan`, and waits for user approval before checking mock calendars and preferences.

The project implements four learning labs:

- **Lab 1:** Structured goal tracking, planning, clarification, drafting, and in-place revision.
- **Lab 2:** Approval-gated tool use, centralized tool execution, availability checking, and ranked slot selection.
- **Lab 3:** Reusable, schema-typed `PlanSkill` and `FormatSkill` modules.
- **Lab 4:** Ephemeral session state vs long-term memory (`KnowledgeStore` for tagged reference rules and `MeetingHistoryStore` for TF-IDF similarity search & action-item carryover).

The project uses deterministic local logic and mock data, so it can be run without external AI or calendar credentials.

## Features

- Accepts a natural-language meeting request.
- Extracts the topic, participants, date, and duration.
- Asks dynamically for only the information that is missing.
- Retrieves prior meeting history and carries over open action items into draft agendas (Lab 4 Memory).
- Generates a structured draft meeting plan using reusable `PlanSkill` (Lab 3 Skills).
- Supports user approval, formatting export via `FormatSkill` (Markdown, Text, HTML), and revision.
- Mutates the existing plan during revisions while preserving its Meeting ID.
- Uses the Lab 2 tool workflow only after explicit approval.
- Reads invitee preferences from mock data.
- Reads calendar availability from mock data.
- Calculates and checks collision-free meeting slots.
- Ranks and displays the Top-K available time slots (up to three).
- Lets the user select a preferred slot.
- Produces a final confirmed meeting plan.

## Application Flow

```text
User Request
    -> Extract meeting information
    -> Check for missing fields
    -> Ask only for missing information
    -> Retrieve Memory (Reference Rules & Prior Meeting History for Action Item Carryover)
    -> Execute PlanSkill to Generate Draft Meeting Blueprint
    -> User Approves, Formats (FormatSkill), or Requests Changes
    -> Revise the existing plan if needed
    -> On approval, execute Lab 2 tools
    -> Read preferences and availability
    -> Calculate and rank valid time slots
    -> Display Top-K slots
    -> User selects a slot
    -> Generate Final Confirmed Meeting Plan
```

During draft generation, the time slot remains `PENDING_VERIFICATION`. The application does not invent availability. After approval, the tool flow checks working hours and busy intervals, ranks verified slots by invitee preferences, and changes the same plan to a confirmed plan after selection.

## Project Structure

```text
Meeting_Organizer_Agent/
├── app/
│   ├── main.py                     # FastAPI application entry point
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── llm.py                  # Deterministic request analysis and plan editing
│   │   └── planner.py              # MeetingOrganizerAgent coordinating skills, memory, and tools
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py               # API routes for sessions, tools, skills, and memory
│   ├── data/
│   │   ├── __init__.py
│   │   └── mock_data.py            # Mock invitee profiles and calendar events
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── session_state.py       # ShortTermSessionState (ephemeral run state)
│   │   ├── store.py               # KnowledgeStore (tagged reference rules)
│   │   └── history.py             # MeetingHistoryStore (TF-IDF similarity search & action carryover)
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py               # Pydantic request, response, plan, skill, and memory schemas
│   ├── services/
│   │   ├── __init__.py
│   │   └── session_service.py       # In-memory session management
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── base.py                # BaseSkill abstract class
│   │   ├── plan_skill.py          # Reusable PlanSkill (skill plan(inputs) -> Plan)
│   │   └── format_skill.py        # Reusable FormatSkill (Markdown/Text/HTML assembly)
│   └── tools/
│       ├── __init__.py
│       ├── calendar_tool.py         # Calendar availability reader
│       ├── invitee_tool.py          # Invitee preference reader
│       ├── calculator_tool.py       # Slot calculation, ranking, and validation
│       └── executor.py              # Centralized tool execution and tracing
├── tests/
│   ├── __init__.py
│   ├── test_agent_loop.py           # Lab 1 agent loop and revision tests
│   ├── test_api.py                  # FastAPI session lifecycle tests
│   ├── test_lab1_lab2_rubric.py     # Lab 1 and Lab 2 rubric checks
│   ├── test_lab3_skills.py          # Lab 3 skill tests (PlanSkill & FormatSkill)
│   ├── test_lab4_memory.py          # Lab 4 memory tests (Session state, Knowledge & History)
│   ├── test_lab3_lab4_rubric.py     # Lab 3 and Lab 4 rubric checks
│   └── test_tools.py                # Lab 2 tool and executor tests
├── demo.py                          # Interactive command-line demonstration
├── pyproject.toml                   # Project metadata and pytest configuration
├── requirements.txt                 # Python dependencies
└── README.md                        # Project documentation
```

## Technologies Used

- Python 3.10 or newer
- FastAPI for the web application and API routes
- Uvicorn for serving the FastAPI application
- Pydantic for typed request, meeting-plan, skill, and memory schemas
- Pytest for automated testing
- HTTPX for API test support

## Installation and Setup

### 1. Clone or download the project

Clone the repository with Git, or download and extract the project ZIP from GitHub.

```bash
git clone <repository-url>
```

### 2. Navigate to the project folder

```powershell
cd Meeting_Organizer_Agent
```

### 3. Create a virtual environment

```powershell
python -m venv .venv
```

### 4. Activate the virtual environment on Windows

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Command Prompt:

```bat
.venv\Scripts\activate.bat
```

### 5. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 6. Run the application

Start the interactive command-line demonstration with:

```powershell
python demo.py
```

The demo prompts for a request, collects missing details, displays the draft, handles revisions, asks for approval, presents ranked slots, and prints the final confirmed plan.

The FastAPI application can also be started with:

```powershell
python -m uvicorn app.main:app --reload
```

When the server is running, API documentation is available at `http://127.0.0.1:8000/docs`.

## Example Usage

An interactive session can look like this:

```text
Describe your meeting request.
> Let's meet to discuss the project

What is the meeting topic?
> Project planning
Who should attend?
> Alice and Bob
How long should the meeting be in minutes?
> 30
What date or date window should be used?
> 2026-09-07

Retrieving memory & executing Lab 3 PlanSkill...

Draft Meeting Plan (Generated via Lab 3 PlanSkill & Lab 4 Memory)
Meeting ID: <generated-id>
Title: Project planning
Duration: 30 minutes
Time Slot: PENDING_VERIFICATION

Choose an action:
[a] Approve and continue to scheduling
[r] Request changes
[f] View formatted document (Lab 3 FormatSkill)
> r
What changes would you like?
> Add a discussion of release risks

Choose an action:
> a

Available time slots (ranked by invitee preferences):
1. 10:00 - 10:30
2. 16:00 - 16:30
3. 16:30 - 17:00

Choose your preferred slot [1-3]:
> 1

Final Confirmed Meeting Plan
Meeting ID: <same generated-id>
Confirmed Time Slot: 10:00-10:30
Status: confirmed
```

The exact ranked slots depend on the participants, date, duration, and mock calendar data.

## Labs Implemented

### Lab 1: Goal -> Plan -> Act -> Observe -> Revise

Lab 1 is implemented by `MeetingOrganizerAgent` and the planner modules. The agent stores meeting requirements as a structured goal, extracts values from free text, identifies missing fields, asks targeted clarification questions, and generates a draft `MeetingPlan` with an agenda, minutes outline, assumptions, and next steps.

Users can request changes to the draft. Revisions mutate the existing plan in place, preserve unchanged fields including the Meeting ID, and record revision history and iteration logs. The draft remains blocked at the approval phase until the user explicitly accepts it.

### Lab 2: Tool-Using Agent

Lab 2 begins at the explicit approval gate. The centralized `ToolExecutor` records each structured call and its result. The tool chain:

1. Reads invitee working hours, time zones, preferred time bands, and buffers.
2. Reads each participant's mock calendar busy intervals.
3. Calculates collision-free slots within the common working window.
4. Ranks valid slots by invitee preferences and presents up to three options.
5. Validates the user's selection and updates the plan to confirmed status.

The available tools are `read_invitee_preferences`, `read_calendar`, `calculate_meeting_slots`, and `validate_slot`. No tool calls are made while the plan is still an unapproved draft.

### Lab 3: Skill Creation (Reusable Plan & Format Skills)

Lab 3 packages repeatable agent capability into schema-typed skills:
- **`PlanSkill` (`skill plan(inputs) -> Plan`)**: Accepts structured parameters and outputs a locked `LockedPlanBlueprint`. Case-agnostic, handling committee meetings, standups, sprint reviews, and project syncs without code changes.
- **`FormatSkill` (`skill format_scheduled(result, template) -> Document`)**: Formats a `MeetingPlan` into standardized Markdown, Plain Text, or HTML documents.

### Lab 4: Memory & Retrieval (Session State vs Stored Knowledge)

Lab 4 isolates ephemeral execution memory from long-term reference archives:
- **`ShortTermSessionState`**: Holds active draft candidates and session iteration logs.
- **`KnowledgeStore`**: Archives domain reference guidelines, searchable via `retrieve_by_tags(tags)`.
- **`MeetingHistoryStore`**: Archives past meetings and decisions, searchable via `retrieve_similar(query_text)` (TF-IDF). Automatically extracts unresolved action items from prior meetings and carries them over into new agendas.

## Testing

The `tests/` folder contains unit, integration, tool, skill, memory, and rubric tests for Labs 1-4. With the virtual environment activated and dependencies installed, run the full suite from the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

The tests cover requirement extraction, dynamic clarification, draft generation, in-place revision, the approval gate, mock calendar and preference tools, slot calculation and ranking, `PlanSkill` & `FormatSkill` schema validation, short-term vs long-term memory separation, tag search, text similarity search, action-item carryover, API session flows, and execution tracing.

