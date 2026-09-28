"""Employee endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import EmployeeCreate, EmployeeDetail, EmployeeOut
from app.db import crud
from app.db.database import get_db
from app.db.models import LeaveRequest, Meeting, OnboardingTask, TaskStatus

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeOut])
def list_employees(db: Session = Depends(get_db)):
    return crud.list_employees(db)


@router.post("", response_model=EmployeeOut, status_code=201)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_none=True)
    if "skills" not in data:
        data["skills"] = []
    if crud.get_employee_by_email(db, data["email"]):
        raise HTTPException(409, "An employee with this email already exists.")
    emp = crud.create_employee(db, data)
    crud.default_leave_balances(db, emp.id)
    crud.log_agent(db, "API", "employee_created", employee_id=emp.id,
                   detail=f"Manual creation of {emp.name} ({emp.role}).")
    return emp


@router.get("/{employee_id}", response_model=EmployeeDetail)
def get_employee(employee_id: str, db: Session = Depends(get_db)):
    emp = crud.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(404, f"Employee {employee_id} not found.")
    # Validate base fields only — avoid from_attributes picking up ORM relationships
    base = EmployeeOut.model_validate(emp).model_dump()
    detail = EmployeeDetail(**base)
    detail.progress = crud.employee_progress(db, employee_id)
    detail.tasks = [_task_out(t, emp.name) for t in crud.list_tasks(db, employee_id)]
    detail.meetings = [_meeting_out(m, emp.name) for m in crud.list_meetings(db, employee_id)]
    detail.leave_requests = [_leave_out(l, emp.name) for l in crud.list_leave_requests(db, employee_id)]
    detail.balances = [
        {"id": b.id, "employee_id": b.employee_id, "leave_type": b.leave_type.value,
         "total_days": b.total_days, "used_days": b.used_days,
         "remaining_days": b.remaining_days}
        for b in crud.list_balances(db, employee_id)
    ]  # dicts validate against BalanceOut
    return detail


def _task_out(t: OnboardingTask, name: str) -> dict:
    d = {c.name: getattr(t, c.name) for c in t.__table__.columns}
    d["status"] = t.status.value
    d["employee_name"] = name
    return d


def _meeting_out(m: Meeting, name: str) -> dict:
    d = {c.name: getattr(m, c.name) for c in m.__table__.columns}
    d["status"] = m.status.value
    d["employee_name"] = name
    return d


def _leave_out(l: LeaveRequest, name: str) -> dict:
    d = {c.name: getattr(l, c.name) for c in l.__table__.columns}
    d["status"] = l.status.value
    d["leave_type"] = l.leave_type.value
    d["employee_name"] = name
    return d
