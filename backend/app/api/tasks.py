"""Onboarding task endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import TaskOut, TaskUpdate
from app.db import crud
from app.db.database import get_db
from app.db.models import TaskStatus

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _task_out(t, employee_name=None) -> dict:
    d = {c.name: getattr(t, c.name) for c in t.__table__.columns}
    d["status"] = t.status.value
    d["employee_name"] = employee_name or (t.employee.name if t.employee else None)
    return d


@router.get("", response_model=list[TaskOut])
def list_tasks(employee_id: str | None = None, status: str | None = None,
               db: Session = Depends(get_db)):
    crud.refresh_overdue_tasks(db)
    tasks = crud.list_tasks(db, employee_id=employee_id, status=status)
    return [_task_out(t) for t in tasks]


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = crud.update_task_status(db, task_id, TaskStatus(payload.status))
    if not task:
        raise HTTPException(404, f"Task {task_id} not found.")
    crud.log_agent(db, "OnboardingAgent", "task_status_updated", employee_id=task.employee_id,
                   detail=f"Task #{task.id} '{task.title}' -> {task.status.value}.")
    return _task_out(task)
