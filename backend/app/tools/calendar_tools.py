"""Calendar tools — a mock calendar service with realistic availability.

Designed so a real provider (Google Calendar / Microsoft Graph) can be swapped
in later: the Calendar Agent only calls the functions in this module, and a
provider class isolates the "external calendar" behavior.
"""
from __future__ import annotations

from datetime import date, time, timedelta

from sqlalchemy.orm import Session

from app.db import crud
from app.db.models import MeetingStatus

WORKDAY_START = time(9, 0)
WORKDAY_END = time(18, 0)
LUNCH = (time(13, 0), time(14, 0))
SLOT_MINUTES = 30


def _to_min(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _to_str(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def next_workday(d: date) -> date:
    while d.weekday() >= 5:  # Sat/Sun
        d += timedelta(days=1)
    return d


def find_available_slot(
    db: Session,
    day: date,
    duration_minutes: int = 60,
    preferred_hour: int = 10,
) -> tuple[str, str] | None:
    """Find a free slot on `day` avoiding existing meetings and lunch hour.

    Mock availability model: working hours 09:00-18:00, Mon-Fri, lunch 13-14.
    """
    if day.weekday() >= 5:
        return None

    busy = [
        (_to_min(m.start_time), _to_min(m.end_time))
        for m in crud.meetings_on_slot(db, day, "00:00", "23:59")
    ]
    busy.append((_to_min("13:00"), _to_min("14:00")))  # lunch block

    # scan outward from the preferred hour
    day_start, day_end = WORKDAY_START.hour * 60, WORKDAY_END.hour * 60
    preferred = preferred_hour * 60
    candidates = sorted(
        range(day_start, day_end - duration_minutes + 1, SLOT_MINUTES),
        key=lambda m: abs(m - preferred),
    )
    for start in candidates:
        end = start + duration_minutes
        if any(start < b_end and end > b_start for b_start, b_end in busy):
            continue
        return _to_str(start), _to_str(end)
    return None


def check_availability(db: Session, day: date, start: str, end: str) -> bool:
    """True if the slot is free (workday, within hours, not lunch, no conflicts)."""
    if day.weekday() >= 5:
        return False
    s, e = _to_min(start), _to_min(end)
    if s < WORKDAY_START.hour * 60 or e > WORKDAY_END.hour * 60 or e <= s:
        return False
    if s < _to_min("14:00") and e > _to_min("13:00"):  # overlaps lunch
        return False
    return not crud.meetings_on_slot(db, day, start, end)


def schedule_meeting(
    db: Session,
    employee_id: str,
    title: str,
    day: date,
    duration_minutes: int = 60,
    participants: list[str] | None = None,
    preferred_hour: int = 10,
):
    """Create a meeting at the next available slot on/after `day`.

    Returns (Meeting|None, note). Tries up to 5 workdays forward.
    """
    d = next_workday(day)
    for _ in range(10):
        slot = find_available_slot(db, d, duration_minutes, preferred_hour)
        if slot:
            meeting = crud.create_meeting(
                db,
                employee_id,
                title=title,
                date=d,
                start_time=slot[0],
                end_time=slot[1],
                participants=participants or [],
                status=MeetingStatus.SCHEDULED,
            )
            return meeting, f"Scheduled {title} on {d.isoformat()} {slot[0]}-{slot[1]}"
        d = next_workday(d + timedelta(days=1))
    return None, f"Could not find an available slot for {title} within 10 workdays"


def reschedule_meeting(
    db: Session, meeting_id: int, new_date: date | None = None,
    new_start: str | None = None, new_end: str | None = None,
):
    """Reschedule with availability check. Returns (Meeting|None, note)."""
    meeting = crud.get_meeting(db, meeting_id)
    if not meeting:
        return None, f"Meeting {meeting_id} not found"

    target_date = new_date or meeting.date
    if new_start and new_end:
        if not check_availability(db, target_date, new_start, new_end):
            return None, f"Slot {target_date} {new_start}-{new_end} is not available"
        updated = crud.update_meeting(db, meeting_id, date=target_date, start_time=new_start, end_time=new_end)
        return updated, f"Rescheduled to {target_date} {new_start}-{new_end}"

    # auto-find a slot on the new date
    duration = _to_min(meeting.end_time) - _to_min(meeting.start_time)
    slot = find_available_slot(db, next_workday(target_date), duration)
    if not slot:
        return None, f"No available slot on {target_date}"
    updated = crud.update_meeting(db, meeting_id, date=target_date, start_time=slot[0], end_time=slot[1])
    return updated, f"Rescheduled to {target_date} {slot[0]}-{slot[1]}"


def cancel_meeting(db: Session, meeting_id: int):
    meeting = crud.get_meeting(db, meeting_id)
    if not meeting:
        return None, f"Meeting {meeting_id} not found"
    updated = crud.update_meeting(db, meeting_id, status=MeetingStatus.CANCELLED)
    return updated, f"Cancelled meeting '{meeting.title}'"
