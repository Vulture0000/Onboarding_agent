"""Leave Agent: interprets leave requests, consults the Policy Agent, and
applies deterministic leave rules via leave_tools (Rule 2).

Flow within the graph:
  leave_agent (phase=intake)  -> policy_agent -> leave_agent (phase=decide)
      -> human_approval (interrupt) if approval required
      -> finalize_leave (after human decision or auto-approval)

The LLM only parses natural language into a structured request. Dates,
balances, approval requirements and status transitions are computed by code.
"""
from __future__ import annotations

import logging
from datetime import date

from app.agents.llm import llm_json
from app.db import crud
from app.db.database import SessionLocal
from app.graph.state import OnboardingState
from app.tools import leave_tools

logger = logging.getLogger(__name__)

PARSE_PROMPT = """Extract the leave request from the message below.
Return ONLY valid JSON: {{"leave_type": "CASUAL|SICK|EARNED", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "reason": string}}
Today's date is {today}. Resolve relative expressions like "next Monday" or "tomorrow" against it.
If a field cannot be determined, use null.

Message: {message}"""


def parse_leave_message(message: str, fallback: dict | None = None) -> dict:
    """LLM parsing with deterministic fallback from an explicit API payload."""
    parsed = llm_json(PARSE_PROMPT.format(today=date.today().isoformat(), message=message[:1500]))
    result = dict(fallback or {})
    if parsed:
        for key in ("leave_type", "start_date", "end_date", "reason"):
            if parsed.get(key):
                result[key] = parsed[key]
    return result


def _coerce_date(value) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def leave_agent_node(state: OnboardingState) -> dict:
    """Runs twice per leave flow: intake phase, then decide phase (after policy context)."""
    db = SessionLocal()
    try:
        phase = state.get("leave_phase", "intake")

        req = dict(state.get("leave_request") or {})
        employee_id = req.get("employee_id") or state.get("employee_id")

        # ---- INTAKE: parse the request and ask the Policy Agent for context ----
        if phase == "intake":
            if state.get("user_message") and not req.get("leave_type"):
                req = parse_leave_message(state["user_message"], req)

            if not employee_id or not req.get("leave_type"):
                crud.log_agent(db, "LeaveAgent", "parse_failed", status="warning",
                               detail="Missing employee_id or leave_type in request.")
                return {"current_agent": "leave_agent",
                        "error": "LeaveAgent needs an employee and a leave type."}

            emp = crud.get_employee(db, employee_id)
            if not emp:
                return {"current_agent": "leave_agent", "error": f"Employee {employee_id} not found."}

            leave_type = leave_tools.parse_leave_type(req["leave_type"])
            if leave_type is None:
                return {"current_agent": "leave_agent",
                        "error": f"Unsupported leave type: {req['leave_type']}"}

            start, end = _coerce_date(req.get("start_date")), _coerce_date(req.get("end_date"))
            err = leave_tools.validate_dates(start, end)
            if err:
                crud.log_agent(db, "LeaveAgent", "validation_failed", employee_id=employee_id,
                               status="warning", detail=err)
                return {"current_agent": "leave_agent", "leave_status": "REJECTED", "error": err}

            crud.log_agent(db, "LeaveAgent", "leave_parsed", employee_id=employee_id,
                           detail=f"{leave_type.value} leave {start} to {end}. Requesting policy context.")

            question = (f"What are the approval rules and entitlements for {leave_type.value} leave "
                        f"of {leave_tools.count_working_days(start, end)} working day(s)?")
            return {
                "current_agent": "leave_agent",
                "leave_phase": "decide",
                "employee_id": employee_id,
                "leave_request": {**req, "employee_id": employee_id,
                                  "leave_type": leave_type.value,
                                  "start_date": start.isoformat(),
                                  "end_date": end.isoformat()},
                "policy_question": question,
                "messages": list(state.get("messages") or []),
            }

        # ---- DECIDE: deterministic evaluation using retrieved policy context ----
        req = dict(state.get("leave_request") or {})
        leave_type = leave_tools.parse_leave_type(req.get("leave_type", ""))
        start, end = _coerce_date(req.get("start_date")), _coerce_date(req.get("end_date"))
        if not leave_type or not start or not end or not employee_id:
            return {"current_agent": "leave_agent", "error": "Incomplete leave request in state."}

        policy_sources = [s.get("source") for s in (state.get("policy_context") or []) if s.get("source")]
        thread_id = (state.get("result") or {}).get("thread_id")

        lr, err, decision = leave_tools.evaluate_and_create(
            db, employee_id, leave_type, start, end,
            reason=req.get("reason"),
            policy_context=state.get("policy_context") or [],
            thread_id=thread_id,
        )
        if err or not lr:
            return {"current_agent": "leave_agent", "leave_status": "REJECTED", "error": err}

        crud.log_agent(
            db, "LeaveAgent", "leave_evaluated", employee_id=employee_id,
            status="warning" if decision.get("requires_approval") else "completed",
            detail=f"{lr.days} day(s) {leave_type.value}: {decision.get('outcome')}. "
                   f"Policy sources: {', '.join(policy_sources) or 'none'}. "
                   + " | ".join(decision.get("messages", [])),
        )

        messages = list(state.get("messages") or [])
        outcome = decision.get("outcome")
        if outcome == "PENDING_APPROVAL":
            messages.append({
                "role": "assistant", "agent": "LeaveAgent",
                "content": f"Leave request #{lr.id} created ({lr.days} day(s) {leave_type.value}). "
                           f"Manager approval required — pausing workflow for human decision.",
            })
        elif outcome == "APPROVED":
            messages.append({
                "role": "assistant", "agent": "LeaveAgent",
                "content": f"Leave request #{lr.id} auto-approved per leave policy "
                           f"({lr.days} day(s) {leave_type.value}, within balance).",
            })
        else:  # REJECTED
            messages.append({
                "role": "assistant", "agent": "LeaveAgent",
                "content": f"Leave request #{lr.id} rejected: " + " ".join(decision.get("messages", [])),
            })

        return {
            "current_agent": "leave_agent",
            "leave_result": decision,
            "leave_status": outcome,
            "requires_human_approval": bool(decision.get("requires_approval")),
            "messages": messages,
            "result": {**(state.get("result") or {}),
                       "leave_request_id": lr.id,
                       "leave_status": outcome,
                       "days": lr.days,
                       "requires_approval": bool(decision.get("requires_approval"))},
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("LeaveAgent failed")
        crud.log_agent(db, "LeaveAgent", "agent_error",
                       employee_id=state.get("employee_id"), status="error", detail=str(exc))
        return {"current_agent": "leave_agent", "error": f"LeaveAgent failed: {exc}"}
    finally:
        db.close()


def finalize_leave_node(state: OnboardingState) -> dict:
    """Runs after the human decision (interrupt resume). Applies the decision
    deterministically via crud.decide_leave_request."""
    db = SessionLocal()
    try:
        leave_id = (state.get("result") or {}).get("leave_request_id")
        decision = (state.get("human_decision") or "").lower()
        if not leave_id or decision not in ("approve", "reject"):
            return {"current_agent": "finalize_leave"}

        lr = crud.decide_leave_request(db, leave_id, approve=(decision == "approve"))
        if lr:
            crud.log_agent(db, "LeaveAgent", "leave_decision_applied", employee_id=lr.employee_id,
                           detail=f"Request #{lr.id} marked {lr.status.value} by human approver.")
            messages = list(state.get("messages") or [])
            messages.append({
                "role": "assistant", "agent": "LeaveAgent",
                "content": f"Human decision applied: leave request #{lr.id} is now {lr.status.value}.",
            })
            return {
                "current_agent": "finalize_leave",
                "leave_status": lr.status.value,
                "messages": messages,
                "result": {**(state.get("result") or {}), "leave_status": lr.status.value},
            }
        return {"current_agent": "finalize_leave"}
    finally:
        db.close()
