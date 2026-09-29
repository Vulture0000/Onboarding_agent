"""Calendar endpoints — meeting CRUD via the Calendar Agent's tools."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import assert_can_view_employee, get_current_user, require_manager
from app.api.schemas import MeetingCreate, MeetingOut, MeetingUpdate
from app.db import crud
from app.db.database import get_db
from app.db.models import MeetingStatus, User
from app.tools import calendar_tools

router = APIRouter(prefix="/api/meetings", tags=["calendar"])


def _meeting_out(m) -> dict:
    d = {c.name: getattr(m, c.name) for c in m.__table__.columns}
    d["status"] = m.status.value
    d["employee_name"] = m.employee.name if m.employee else None
    return d


@router.get("", response_model=list[MeetingOut])
def list_meetings(employee_id: str | None = None, upcoming: bool = False,
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    meetings = crud.list_meetings(db, employee_id=employee_id, upcoming_only=upcoming, user=user)
    return [_meeting_out(m) for m in meetings]


@router.post("", response_model=MeetingOut, status_code=201)
def create_meeting(payload: MeetingCreate, db: Session = Depends(get_db),
                   user: User = Depends(require_manager)):
    """Scheduling is a manager/HR action, scoped to employees they can see."""
    assert_can_view_employee(db, user, payload.employee_id)
    emp = crud.get_employee(db, payload.employee_id)
    if not emp:
        raise HTTPException(404, f"Employee {payload.employee_id} not found.")

    participants = payload.participants or [emp.name]
    if payload.start_time and payload.end_time:
        if not calendar_tools.check_availability(db, payload.date, payload.start_time, payload.end_time):
            raise HTTPException(409, "Requested slot is not available (conflict, outside work hours, lunch, or weekend).")
        meeting = crud.create_meeting(
            db, payload.employee_id, title=payload.title, date=payload.date,
            start_time=payload.start_time, end_time=payload.end_time,
            participants=participants, status=MeetingStatus.SCHEDULED,
        )
        note = f"Meeting '{meeting.title}' created for {meeting.date} {meeting.start_time}-{meeting.end_time}."
    else:
        # let the calendar tool find an available slot
        duration = 60
        meeting, note = calendar_tools.schedule_meeting(
            db, payload.employee_id, payload.title, payload.date,
            duration_minutes=duration, participants=participants,
        )
        if not meeting:
            raise HTTPException(409, note)

    crud.log_agent(db, "CalendarAgent", "meeting_created", employee_id=payload.employee_id, detail=note)
    return _meeting_out(meeting)


@router.patch("/{meeting_id}", response_model=MeetingOut)
def update_meeting(meeting_id: int, payload: MeetingUpdate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    meeting = crud.get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(404, f"Meeting {meeting_id} not found.")
    # Employees may only mark their own meetings complete; reschedule/cancel is manager/HR.
    is_owner = user.role.value == "EMPLOYEE" and meeting.employee_id == user.employee_id
    if user.role.value == "EMPLOYEE":
        if not is_owner:
            raise HTTPException(403, "You do not have access to this meeting.")
        if payload.status != "COMPLETED" or payload.date or payload.start_time:
            raise HTTPException(403, "Employees may only mark their own meetings as completed.")

    if payload.status == "CANCELLED":
        updated, note = calendar_tools.cancel_meeting(db, meeting_id)
    elif payload.date or payload.start_time:
        updated, note = calendar_tools.reschedule_meeting(
            db, meeting_id, new_date=payload.date,
            new_start=payload.start_time, new_end=payload.end_time,
        )
        if not updated:
            raise HTTPException(409, note)
    else:
        updated = crud.update_meeting(db, meeting_id, status=payload.status)
        note = f"Meeting #{meeting_id} status set to {payload.status}."

    crud.log_agent(db, "CalendarAgent", "meeting_updated", employee_id=meeting.employee_id,
                   detail=f"{note} (by {user.name})")
    return _meeting_out(updated)
