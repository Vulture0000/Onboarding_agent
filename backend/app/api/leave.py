"""Leave endpoints — requests run through the LangGraph leave workflow;
approve/reject resume the interrupted graph (human-in-the-loop)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import BalanceOut, LeaveCreate, LeaveOut
from app.db import crud
from app.db.database import get_db
from app.db.models import LeaveStatus
from app.graph import workflow

router = APIRouter(prefix="/api/leave", tags=["leave"])


def _leave_out(l) -> dict:
    d = {c.name: getattr(l, c.name) for c in l.__table__.columns}
    d["status"] = l.status.value
    d["leave_type"] = l.leave_type.value
    d["employee_name"] = l.employee.name if l.employee else None
    return d


@router.get("", response_model=list[LeaveOut])
def list_leave(employee_id: str | None = None, status: str | None = None,
               db: Session = Depends(get_db)):
    requests = crud.list_leave_requests(db, employee_id=employee_id, status=status)
    return [_leave_out(l) for l in requests]


@router.get("/balances", response_model=list[BalanceOut])
def list_balances(employee_id: str | None = None, db: Session = Depends(get_db)):
    balances = crud.list_balances(db, employee_id=employee_id)
    return [
        {"id": b.id, "employee_id": b.employee_id, "leave_type": b.leave_type.value,
         "total_days": b.total_days, "used_days": b.used_days,
         "remaining_days": b.remaining_days}
        for b in balances
    ]


@router.post("", response_model=LeaveOut, status_code=201)
def create_leave(payload: LeaveCreate, db: Session = Depends(get_db)):
    """Run the leave workflow: LeaveAgent -> PolicyAgent -> (HumanApproval)."""
    emp = crud.get_employee(db, payload.employee_id)
    if not emp:
        raise HTTPException(404, f"Employee {payload.employee_id} not found.")

    thread_id = f"leave-{uuid.uuid4().hex[:10]}"
    try:
        result = workflow.run_workflow(
            {
                "request_type": "leave",
                "employee_id": payload.employee_id,
                "user_message": payload.reason or "",
                "leave_request": {
                    "employee_id": payload.employee_id,
                    "leave_type": payload.leave_type,
                    "start_date": payload.start_date.isoformat(),
                    "end_date": payload.end_date.isoformat(),
                    "reason": payload.reason,
                },
                "result": {"thread_id": thread_id},
                "messages": [],
            },
            thread_id=thread_id,
        )
    except Exception as exc:  # noqa: BLE001
        crud.log_agent(db, "Supervisor", "workflow_error", employee_id=payload.employee_id,
                       status="error", detail=str(exc))
        raise HTTPException(500, "Leave workflow failed. Check agent activity for details.") from exc

    if result.get("error"):
        raise HTTPException(422, result["error"])

    leave_id = (result.get("result") or result).get("leave_request_id") or result.get("leave_request_id")
    lr = crud.get_leave_request(db, leave_id) if leave_id else None
    if not lr:
        raise HTTPException(500, "Leave request was not created.")
    if lr.thread_id != thread_id:
        lr.thread_id = thread_id
        db.commit()
        db.refresh(lr)
    return _leave_out(lr)


def _decide(leave_id: int, approve: bool, db: Session) -> dict:
    lr = crud.get_leave_request(db, leave_id)
    if not lr:
        raise HTTPException(404, f"Leave request {leave_id} not found.")
    if lr.status != LeaveStatus.PENDING:
        raise HTTPException(409, f"Leave request is already {lr.status.value}.")

    decision = "approve" if approve else "reject"
    resumed = False
    # Preferred path: resume the interrupted LangGraph thread (human-in-the-loop)
    if lr.thread_id and workflow.thread_is_interrupted(lr.thread_id):
        try:
            workflow.resume_workflow(lr.thread_id, decision)
            resumed = True
        except Exception as exc:  # noqa: BLE001
            crud.log_agent(db, "Supervisor", "resume_failed", employee_id=lr.employee_id,
                           status="error", detail=f"Graph resume failed, applying DB fallback: {exc}")

    # Fallback (or if the graph never interrupted): deterministic DB update
    if not resumed:
        lr = crud.decide_leave_request(db, leave_id, approve=approve)
        if not lr:
            raise HTTPException(409, "Could not apply decision (request is no longer pending).")
        crud.log_agent(db, "LeaveAgent", "leave_decision_applied", employee_id=lr.employee_id,
                       detail=f"Request #{lr.id} marked {lr.status.value} by HR Admin (fallback path).")

    db.refresh(lr)
    return _leave_out(lr)


@router.post("/{leave_id}/approve", response_model=LeaveOut)
def approve_leave(leave_id: int, db: Session = Depends(get_db)):
    return _decide(leave_id, True, db)


@router.post("/{leave_id}/reject", response_model=LeaveOut)
def reject_leave(leave_id: int, db: Session = Depends(get_db)):
    return _decide(leave_id, False, db)
