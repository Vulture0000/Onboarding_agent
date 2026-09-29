"""Self-service endpoints — everything here derives employee_id from the token,
never from a client-supplied parameter.

  GET  /api/me/summary       -> my tasks / meetings / leave / balances in one call
  GET  /api/me/tasks         -> my onboarding tasks
  PATCH /api/me/tasks/{id}   -> update status of MY task only
  GET  /api/me/meetings      -> my meetings
  GET  /api/me/leave         -> my leave requests
  GET  /api/me/leave/balances-> my leave balances
  POST /api/me/leave         -> submit MY leave request (runs the LangGraph workflow)
  GET  /api/me/profile       -> my employee profile + progress
  GET  /api/team             -> manager: my direct reports (empty for others)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_manager
from app.api.schemas import (
    BalanceOut,
    EmployeeDetail,
    EmployeeOut,
    LeaveCreate,
    LeaveOut,
    MeetingOut,
    MyLeaveCreate,
    TaskOut,
    TaskUpdate,
)
from app.db import crud
from app.db.database import get_db
from app.db.models import OnboardingTask, Role, TaskStatus, User

router = APIRouter(prefix="/api", tags=["self-service"])


def _task_out(t) -> dict:
    d = {c.name: getattr(t, c.name) for c in t.__table__.columns}
    d["status"] = t.status.value
    d["employee_name"] = t.employee.name if t.employee else None
    return d


def _meeting_out(m) -> dict:
    d = {c.name: getattr(m, c.name) for c in m.__table__.columns}
    d["status"] = m.status.value
    d["employee_name"] = m.employee.name if m.employee else None
    return d


def _leave_out(l) -> dict:
    d = {c.name: getattr(l, c.name) for c in l.__table__.columns}
    d["status"] = l.status.value
    d["leave_type"] = l.leave_type.value
    d["employee_name"] = l.employee.name if l.employee else None
    return d


def _balance_out(b) -> dict:
    return {
        "id": b.id, "employee_id": b.employee_id, "leave_type": b.leave_type.value,
        "total_days": b.total_days, "used_days": b.used_days, "remaining_days": b.remaining_days,
    }


def _require_linked_account(user: User) -> str:
    """HR accounts have no employee record; every /me endpoint below needs one."""
    if not user.employee_id:
        raise HTTPException(
            400,
            f"This account is not linked to an employee record (role={user.role.value}). "
            "Use the admin endpoints instead.",
        )
    return user.employee_id


def _my_profile_detail(db: Session, employee_id: str) -> EmployeeDetail:
    emp = crud.get_employee(db, employee_id)
    detail = EmployeeDetail(
        **EmployeeOut.model_validate(emp).model_dump()
    )
    detail.progress = crud.employee_progress(db, employee_id)
    detail.tasks = [_task_out(t) for t in crud.list_tasks(db, employee_id)]
    detail.meetings = [_meeting_out(m) for m in crud.list_meetings(db, employee_id)]
    detail.leave_requests = [_leave_out(l) for l in crud.list_leave_requests(db, employee_id)]
    detail.balances = [_balance_out(b) for b in crud.list_balances(db, employee_id)]
    return detail


@router.get("/me/profile", response_model=EmployeeDetail)
def my_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _my_profile_detail(db, _require_linked_account(user))


@router.get("/me/tasks", response_model=list[TaskOut])
def my_tasks(status: str | None = None, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    employee_id = _require_linked_account(user)
    crud.refresh_overdue_tasks(db)
    return [_task_out(t) for t in crud.list_tasks(db, employee_id=employee_id, status=status)]


@router.patch("/me/tasks/{task_id}", response_model=TaskOut)
def update_my_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """Employees may only move their OWN tasks, never anyone else's."""
    employee_id = _require_linked_account(user)
    task = db.get(OnboardingTask, task_id)
    if not task:
        raise HTTPException(404, f"Task {task_id} not found.")
    if task.employee_id != employee_id:
        raise HTTPException(403, "You can only update tasks assigned to you.")
    task.status = TaskStatus(payload.status)
    db.commit()
    db.refresh(task)
    crud.log_agent(db, "OnboardingAgent", "task_status_updated", employee_id=employee_id,
                   detail=f"{user.name} set task #{task.id} '{task.title}' -> {task.status.value}.")
    return _task_out(task)


@router.get("/me/meetings", response_model=list[MeetingOut])
def my_meetings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    employee_id = _require_linked_account(user)
    return [_meeting_out(m) for m in crud.list_meetings(db, employee_id=employee_id)]


@router.get("/me/leave", response_model=list[LeaveOut])
def my_leave(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    employee_id = _require_linked_account(user)
    return [_leave_out(l) for l in crud.list_leave_requests(db, employee_id=employee_id)]


@router.get("/me/leave/balances", response_model=list[BalanceOut])
def my_balances(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    employee_id = _require_linked_account(user)
    return [_balance_out(b) for b in crud.list_balances(db, employee_id=employee_id)]


@router.post("/me/leave", response_model=LeaveOut, status_code=201)
def create_my_leave(payload: MyLeaveCreate, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    from app.api.leave import create_leave_for_employee

    employee_id = _require_linked_account(user)
    # employee_id is injected server-side from the token, ignoring anything in the body.
    scoped = LeaveCreate(
        employee_id=employee_id,
        leave_type=payload.leave_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
    )
    return create_leave_for_employee(db, employee_id, scoped, requested_by=user.name)


@router.get("/me/summary")
def my_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """One call for the employee home screen: counters + upcoming + pending items."""
    employee_id = _require_linked_account(user)
    crud.refresh_overdue_tasks(db)

    tasks = crud.list_tasks(db, employee_id=employee_id)
    by_status: dict[str, int] = {}
    for t in tasks:
        by_status[t.status.value] = by_status.get(t.status.value, 0) + 1

    leave = crud.list_leave_requests(db, employee_id=employee_id)
    progress = crud.employee_progress(db, employee_id)

    return {
        "employee_id": employee_id,
        "name": user.name,
        "progress": progress,
        "tasks": [_task_out(t) for t in tasks],
        "tasks_by_status": by_status,
        "meetings": [_meeting_out(m) for m in crud.list_meetings(db, employee_id=employee_id)],
        "upcoming_meetings": [
            _meeting_out(m) for m in crud.list_meetings(db, employee_id=employee_id, upcoming_only=True)
        ],
        "leave": [_leave_out(l) for l in leave],
        "pending_leave": [_leave_out(l) for l in leave if l.status.value == "PENDING"],
        "balances": [_balance_out(b) for b in crud.list_balances(db, employee_id=employee_id)],
    }


@router.get("/team")
def my_team(db: Session = Depends(get_db), user: User = Depends(require_manager)):
    """Manager view: direct reports with their task progress and pending approvals."""
    if user.role != Role.MANAGER or not user.employee_id:
        return []

    reports = []
    for emp_id in crud.team_employee_ids(db, user.employee_id):
        emp = crud.get_employee(db, emp_id)
        if not emp:
            continue
        pending = [
            _leave_out(l)
            for l in crud.list_leave_requests(db, employee_id=emp_id, status="PENDING")
            if l.requires_approval
        ]
        reports.append({
            "id": emp.id,
            "name": emp.name,
            "email": emp.email,
            "role": emp.role,
            "department": emp.department,
            "joining_date": emp.joining_date.isoformat(),
            "status": emp.status,
            **crud.employee_progress(db, emp_id),
            "pending_leave": pending,
        })
    return reports


@router.get("/team/{employee_id}", response_model=EmployeeDetail)
def team_member_detail(employee_id: str, db: Session = Depends(get_db),
                       user: User = Depends(require_manager)):
    """Full record for one report. Managers only get their own direct reports."""
    if not crud.can_access_employee(db, user, employee_id):
        raise HTTPException(403, "That employee is not on your team.")
    if not crud.get_employee(db, employee_id):
        raise HTTPException(404, f"Employee {employee_id} not found.")
    return _my_profile_detail(db, employee_id)