"""Agent endpoints: activity logs, generic graph invocation, dashboard stats."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import AgentLogOut, AgentRunRequest, AgentRunResponse
from app.config import settings
from app.db import crud
from app.db.database import get_db
from app.graph import workflow

router = APIRouter(prefix="/api", tags=["agents"])


@router.get("/agent/logs", response_model=list[AgentLogOut])
def get_agent_logs(limit: int = 100, db: Session = Depends(get_db)):
    return crud.list_agent_logs(db, limit=min(limit, 500))


@router.get("/agent/status")
def agent_status():
    """LLM/RAG availability — lets the UI show system health honestly."""
    from app.rag.retriever import get_vector_store

    return {
        "llm_enabled": settings.llm_enabled,
        "llm_model": settings.gemini_model if settings.llm_enabled else None,
        "embedding_model": settings.gemini_embedding_model if settings.llm_enabled else None,
        "vector_store_ready": get_vector_store() is not None,
        "retrieval_mode": "faiss" if get_vector_store() is not None else "keyword-fallback",
    }


@router.post("/agent/run", response_model=AgentRunResponse)
def run_agent(payload: AgentRunRequest, db: Session = Depends(get_db)):
    """Generic entry point: send a message/request through the LangGraph supervisor."""
    if not payload.message and not payload.request_type:
        raise HTTPException(400, "Provide a message or request_type.")

    if payload.employee_id and not crud.get_employee(db, payload.employee_id):
        raise HTTPException(404, f"Employee {payload.employee_id} not found.")

    thread_id = f"run-{uuid.uuid4().hex[:10]}"
    initial: dict = {
        "request_type": payload.request_type or "",
        "user_message": payload.message or "",
        "employee_id": payload.employee_id or "",
        "result": {"thread_id": thread_id},
        "messages": [],
    }
    if payload.leave_request:
        initial["leave_request"] = payload.leave_request
    if payload.meeting_request:
        initial["meetings"] = [payload.meeting_request]

    try:
        result = workflow.run_workflow(initial, thread_id=thread_id)
    except Exception as exc:  # noqa: BLE001
        crud.log_agent(db, "Supervisor", "workflow_error", status="error", detail=str(exc))
        raise HTTPException(500, "Agent workflow failed. Check agent activity for details.") from exc

    return AgentRunResponse(**result)


@router.get("/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    crud.refresh_overdue_tasks(db)
    stats = crud.dashboard_stats(db)

    employees = crud.list_employees(db)
    recent = []
    for emp in employees[:5]:
        progress = crud.employee_progress(db, emp.id)
        recent.append({
            "id": emp.id, "name": emp.name, "role": emp.role, "department": emp.department,
            "joining_date": emp.joining_date.isoformat(), "status": emp.status,
            **progress,
        })

    upcoming = [
        {"id": m.id, "employee_id": m.employee_id,
         "employee_name": m.employee.name if m.employee else None,
         "title": m.title, "date": m.date.isoformat(),
         "start_time": m.start_time, "end_time": m.end_time}
        for m in crud.list_meetings(db, upcoming_only=True)[:6]
    ]

    pending = [
        {"id": l.id, "employee_id": l.employee_id,
         "employee_name": l.employee.name if l.employee else None,
         "leave_type": l.leave_type.value, "start_date": l.start_date.isoformat(),
         "end_date": l.end_date.isoformat(), "days": l.days, "reason": l.reason}
        for l in crud.list_leave_requests(db, status="PENDING")
        if l.requires_approval
    ]

    activity = [
        {"id": a.id, "agent": a.agent, "action": a.action, "status": a.status,
         "detail": a.detail, "employee_id": a.employee_id,
         "timestamp": a.timestamp.isoformat()}
        for a in crud.list_agent_logs(db, limit=8)
    ]

    return {
        **stats,
        "recent_employees": recent,
        "upcoming_meetings_list": upcoming,
        "pending_approvals": pending,
        "recent_activity": activity,
    }
