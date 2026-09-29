"""Onboarding task endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas import TaskOut, TaskUpdate
from app.db import crud
from app.db.database import get_db
from app.db.models import OnboardingTask, TaskStatus, User

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _task_out(t, employee_name=None) -> dict:
    d = {c.name: getattr(t, c.name) for c in t.__table__.columns}
    d["status"] = t.status.value
    d["employee_name"] = employee_name or (t.employee.name if t.employee else None)
    return d


@router.get("", response_model=list[TaskOut])
def list_tasks(employee_id: str | None = None, status: str | None = None,
               db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Results are always clipped to the caller's visibility scope."""
    crud.refresh_overdue_tasks(db)
    tasks = crud.list_tasks(db, employee_id=employee_id, status=status, user=user)
    return [_task_out(t) for t in tasks]


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    existing = db.get(OnboardingTask, task_id)
    if not existing:
        raise HTTPException(404, f"Task {task_id} not found.")
    # Authorize BEFORE mutating.
    if not crud.can_access_employee(db, user, existing.employee_id):
        raise HTTPException(403, "You do not have access to this employee's tasks.")
    task = crud.update_task_status(db, task_id, TaskStatus(payload.status))
    crud.log_agent(db, "OnboardingAgent", "task_status_updated", employee_id=task.employee_id,
                   detail=f"Task #{task.id} '{task.title}' -> {task.status.value} by {user.name}.")
    return _task_out(task)
