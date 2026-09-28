"""LangGraph StateGraph wiring the supervisor and the five agents together.

Flows:
  Resume upload:  supervisor -> resume_agent -> onboarding_agent -> calendar_agent -> END
  Leave request:  supervisor -> leave_agent(intake) -> policy_agent -> leave_agent(decide)
                     -> human_approval (interrupt) -> finalize_leave -> END
                     or -> finalize_leave -> END (auto-approve / reject)
  Policy query:   supervisor -> policy_agent -> END
  Meeting:        supervisor -> calendar_agent -> END

The graph is compiled with a SQLite checkpointer so human-in-the-loop
interrupt/resume survives across API requests (and server restarts).
"""
from __future__ import annotations

import logging
import threading

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command, interrupt
import sqlite3

from app.agents.calendar_agent import calendar_agent_node
from app.agents.leave_agent import finalize_leave_node, leave_agent_node
from app.agents.onboarding_agent import onboarding_agent_node
from app.agents.policy_agent import policy_agent_node
from app.agents.resume_agent import resume_agent_node
from app.agents.supervisor import route_from_supervisor, supervisor_node
from app.config import settings
from app.db import crud
from app.db.database import SessionLocal
from app.graph.state import OnboardingState

logger = logging.getLogger(__name__)

_checkpointer = None
_graph = None
_lock = threading.Lock()


def _make_checkpointer():
    """SQLite-backed checkpointer (persistent interrupts), MemorySaver fallback."""
    try:
        db_path = settings.data_dir / "checkpoints.db"
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        return SqliteSaver(conn)
    except Exception as exc:  # noqa: BLE001
        logger.warning("SqliteSaver unavailable (%s); using MemorySaver.", exc)
        return MemorySaver()


def human_approval_node(state: OnboardingState) -> dict:
    """Pause the graph until a human approves/rejects via the UI.

    `interrupt()` checkpoints the state and raises out of the graph; the API
    resumes it later with Command(resume={"decision": ...}).
    """
    db = SessionLocal()
    try:
        result = state.get("result") or {}
        leave_id = result.get("leave_request_id")
        detail = f"Leave request #{leave_id} paused for manager approval."
        # The node re-executes on resume; avoid duplicate log entries.
        from app.db.models import AgentLog
        from sqlalchemy import select

        already_logged = db.scalar(
            select(AgentLog).where(AgentLog.action == "awaiting_human_approval",
                                   AgentLog.detail == detail).limit(1)
        )
        if not already_logged:
            crud.log_agent(
                db, "Supervisor", "awaiting_human_approval",
                employee_id=state.get("employee_id"), status="warning",
                detail=detail,
            )
    finally:
        db.close()

    payload = interrupt({
        "type": "leave_approval",
        "leave_request_id": (state.get("result") or {}).get("leave_request_id"),
        "employee_id": state.get("employee_id"),
        "leave_request": state.get("leave_request"),
        "reason": "Manager approval required per leave policy.",
    })
    decision = (payload or {}).get("decision", "reject")
    return {"human_decision": decision, "current_agent": "human_approval"}


# --------------------------------------------------------------------------- #
# Conditional edges
# --------------------------------------------------------------------------- #

def route_after_resume(state: OnboardingState) -> str:
    if state.get("error") and "already exists" not in state.get("error", ""):
        return END
    return "onboarding_agent"


def route_after_onboarding(state: OnboardingState) -> str:
    if state.get("error"):
        return END
    return "calendar_agent"


def route_after_leave(state: OnboardingState) -> str:
    if state.get("error"):
        return END
    if state.get("leave_phase") == "decide" and state.get("leave_result"):
        # decide pass done
        if state.get("requires_human_approval") and state.get("leave_status") == "PENDING_APPROVAL":
            return "human_approval"
        return "finalize_leave"
    # intake pass done -> ask the Policy Agent
    return "policy_agent"


def route_after_policy(state: OnboardingState) -> str:
    # If we're inside a leave flow, hand control back to the Leave Agent
    if state.get("request_type") == "leave" and state.get("leave_phase") == "decide":
        return "leave_agent"
    return END


def build_graph():
    builder = StateGraph(OnboardingState)

    builder.add_node("supervisor", supervisor_node)
    builder.add_node("resume_agent", resume_agent_node)
    builder.add_node("onboarding_agent", onboarding_agent_node)
    builder.add_node("calendar_agent", calendar_agent_node)
    builder.add_node("leave_agent", leave_agent_node)
    builder.add_node("policy_agent", policy_agent_node)
    builder.add_node("human_approval", human_approval_node)
    builder.add_node("finalize_leave", finalize_leave_node)

    builder.set_entry_point("supervisor")

    builder.add_conditional_edges(
        "supervisor", route_from_supervisor,
        ["resume_agent", "onboarding_agent", "calendar_agent",
         "leave_agent", "policy_agent", END],
    )
    builder.add_conditional_edges("resume_agent", route_after_resume, ["onboarding_agent", END])
    builder.add_conditional_edges("onboarding_agent", route_after_onboarding, ["calendar_agent", END])
    builder.add_edge("calendar_agent", END)
    builder.add_conditional_edges(
        "leave_agent", route_after_leave, ["policy_agent", "human_approval", "finalize_leave", END]
    )
    builder.add_conditional_edges("policy_agent", route_after_policy, ["leave_agent", END])
    builder.add_edge("human_approval", "finalize_leave")
    builder.add_edge("finalize_leave", END)

    return builder.compile(checkpointer=_make_checkpointer())


def get_graph():
    global _graph
    if _graph is None:
        with _lock:
            if _graph is None:
                _graph = build_graph()
    return _graph


# --------------------------------------------------------------------------- #
# Invocation helpers used by the API layer
# --------------------------------------------------------------------------- #

def run_workflow(initial_state: dict, thread_id: str) -> dict:
    """Run (or start) the graph and return the API-facing result dict."""
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    final = graph.invoke(initial_state, config=config)
    return summarize(final, thread_id)


def resume_workflow(thread_id: str, decision: str) -> dict:
    """Resume an interrupted leave flow with the human decision."""
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    final = graph.invoke(Command(resume={"decision": decision}), config=config)
    return summarize(final, thread_id)


def thread_is_interrupted(thread_id: str) -> bool:
    """True if the thread is currently paused at the human_approval interrupt."""
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    try:
        snapshot = graph.get_state(config)
    except Exception:  # noqa: BLE001
        return False
    return bool(snapshot and snapshot.next)


def summarize(final_state: dict, thread_id: str) -> dict:
    result = dict(final_state.get("result") or {})
    result.update({
        "thread_id": thread_id,
        "messages": final_state.get("messages") or [],
        "error": final_state.get("error"),
        "requires_human_approval": bool(final_state.get("requires_human_approval"))
        and final_state.get("leave_status") == "PENDING_APPROVAL",
        "leave_status": final_state.get("leave_status"),
        "policy_answer": final_state.get("policy_answer"),
        "policy_context": final_state.get("policy_context") or [],
        "employee_data": final_state.get("employee_data"),
        "resume_data": final_state.get("resume_data"),
        "meetings": final_state.get("meetings") or [],
    })
    return result
