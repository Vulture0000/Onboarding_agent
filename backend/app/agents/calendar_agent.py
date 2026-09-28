"""Calendar Agent: schedules onboarding meetings via the mock calendar tools.

All actions go through tools (Rule 1): availability checks, conflict
resolution and persistence are deterministic. A real Google Calendar /
Microsoft Graph provider can replace app.tools.calendar_tools later without
changing this agent.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from app.db import crud
from app.db.database import SessionLocal
from app.graph.state import OnboardingState
from app.tools import calendar_tools

logger = logging.getLogger(__name__)

# Standard onboarding meeting set: (title, day_offset, duration_min, preferred_hour)
MEETING_PLAN = [
    ("HR Orientation", 1, 60, 10),
    ("Manager 1:1", 1, 30, 14),
    ("Team Introduction", 2, 60, 11),
    ("Mentor Meeting", 3, 30, 15),
    ("Security Training", 2, 60, 16),
    ("Project Introduction", 4, 60, 10),
]


def generate_onboarding_meetings(db, employee_id: str, joining: date, employee_name: str,
                                 manager: str | None, mentor: str | None) -> list:
    """Schedule the standard onboarding meeting set for a new employee."""
    created = []
    for title, offset, duration, hour in MEETING_PLAN:
        participants = [employee_name, "HR Team"]
        if manager and "Manager" in title:
            participants.append(manager)
        if mentor and "Mentor" in title:
            participants.append(mentor)
        meeting, note = calendar_tools.schedule_meeting(
            db, employee_id, title,
            day=joining + timedelta(days=offset - 1),
            duration_minutes=duration,
            participants=participants,
            preferred_hour=hour,
        )
        if meeting:
            created.append(meeting)
            crud.log_agent(db, "CalendarAgent", "meeting_scheduled", employee_id=employee_id,
                           detail=f"{note} with {', '.join(participants)}")
        else:
            crud.log_agent(db, "CalendarAgent", "scheduling_failed", employee_id=employee_id,
                           status="warning", detail=note)
    return created


def calendar_agent_node(state: OnboardingState) -> dict:
    db = SessionLocal()
    try:
        employee_id = state.get("employee_id")
        if not employee_id:
            return {"current_agent": "calendar_agent",
                    "error": "CalendarAgent needs an employee_id."}

        emp = crud.get_employee(db, employee_id)
        if not emp:
            return {"current_agent": "calendar_agent", "error": f"Employee {employee_id} not found."}

        # If an explicit meeting request came in, handle just that
        meeting_req = state.get("meetings") or []
        if meeting_req and isinstance(meeting_req[0], dict) and meeting_req[0].get("title"):
            req = meeting_req[0]
            day = req.get("date")
            day = date.fromisoformat(day) if isinstance(day, str) else (day or date.today())
            meeting, note = calendar_tools.schedule_meeting(
                db, employee_id, req["title"], day,
                duration_minutes=req.get("duration_minutes", 60),
                participants=req.get("participants") or [emp.name],
                preferred_hour=req.get("preferred_hour", 10),
            )
            crud.log_agent(db, "CalendarAgent", "meeting_requested", employee_id=employee_id,
                           status="completed" if meeting else "warning", detail=note)
            messages = list(state.get("messages") or [])
            messages.append({"role": "assistant", "agent": "CalendarAgent", "content": note})
            return {
                "current_agent": "calendar_agent",
                "meetings": [{"id": meeting.id, "title": meeting.title,
                              "date": meeting.date.isoformat(),
                              "start_time": meeting.start_time,
                              "end_time": meeting.end_time,
                              "status": meeting.status.value}] if meeting else [],
                "messages": messages,
                "result": {**(state.get("result") or {}), "meeting_note": note},
            }

        # Default: generate the full onboarding meeting set
        existing = [m for m in crud.list_meetings(db, employee_id)
                    if m.status.value == "SCHEDULED"]
        existing_titles = {m.title for m in existing}
        meetings = generate_onboarding_meetings(
            db, employee_id, emp.joining_date, emp.name, emp.manager, emp.mentor,
        )
        meetings = [m for m in meetings if m.title not in existing_titles] or meetings

        crud.log_agent(db, "CalendarAgent", "onboarding_meetings", employee_id=employee_id,
                       detail=f"Scheduled {len(meetings)} onboarding meetings for {emp.name}.")
        messages = list(state.get("messages") or [])
        messages.append({
            "role": "assistant", "agent": "CalendarAgent",
            "content": f"Scheduled {len(meetings)} onboarding meetings for {emp.name}: "
                       + ", ".join(f"{m.title} ({m.date} {m.start_time})" for m in meetings),
        })
        return {
            "current_agent": "calendar_agent",
            "meetings": [
                {"id": m.id, "title": m.title, "date": m.date.isoformat(),
                 "start_time": m.start_time, "end_time": m.end_time,
                 "participants": m.participants, "status": m.status.value}
                for m in meetings
            ],
            "messages": messages,
            "result": {**(state.get("result") or {}), "meetings_scheduled": len(meetings)},
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("CalendarAgent failed")
        crud.log_agent(db, "CalendarAgent", "agent_error",
                       employee_id=state.get("employee_id"), status="error", detail=str(exc))
        return {"current_agent": "calendar_agent", "error": f"CalendarAgent failed: {exc}"}
    finally:
        db.close()
