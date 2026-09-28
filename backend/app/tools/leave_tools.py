"""Leave tools — ALL critical leave business logic lives here (Rule 2).

The LLM may interpret a user's natural-language request, but date validation,
balance checks, approval requirements, and status transitions are computed by
this deterministic code and never delegated to the model.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.db import crud
from app.db.models import LeaveRequest, LeaveStatus, LeaveType

# Approval rules (mirror leave_policy.txt)
AUTO_APPROVE_MAX_DAYS = 2          # CL/SL up to 2 consecutive days auto-approve
ALWAYS_REQUIRES_APPROVAL = {LeaveType.EARNED}
ADVANCE_NOTICE_DAYS = 3            # non-emergency requests should be 3 working days ahead


def parse_leave_type(value: str) -> LeaveType | None:
    v = (value or "").strip().lower()
    mapping = {
        "casual": LeaveType.CASUAL, "cl": LeaveType.CASUAL, "casual leave": LeaveType.CASUAL,
        "sick": LeaveType.SICK, "sl": LeaveType.SICK, "sick leave": LeaveType.SICK,
        "earned": LeaveType.EARNED, "el": LeaveType.EARNED, "earned leave": LeaveType.EARNED,
        "pl": LeaveType.EARNED, "privileged": LeaveType.EARNED,
    }
    if v in mapping:
        return mapping[v]
    for key, lt in mapping.items():
        if key in v:
            return lt
    try:
        return LeaveType(v.upper())
    except ValueError:
        return None


def count_working_days(start: date, end: date) -> int:
    days, d = 0, start
    while d <= end:
        if d.weekday() < 5:
            days += 1
        d += timedelta(days=1)
    return days


def validate_dates(start: date, end: date) -> str | None:
    """Return an error message, or None if the dates are valid."""
    if not start or not end:
        return "Start date and end date are required."
    if end < start:
        return "End date cannot be before start date."
    if end < date.today() - timedelta(days=7):
        return "Leave dates are too far in the past to process."
    if start > date.today() + timedelta(days=365):
        return "Leave dates are more than a year in the future."
    return None


def check_balance(db: Session, employee_id: str, leave_type: LeaveType, days: int) -> tuple[bool, int, str]:
    """Return (ok, remaining, message)."""
    bal = crud.get_balance(db, employee_id, leave_type)
    if bal is None:
        return False, 0, f"No {leave_type.value} leave balance record found."
    if days > bal.remaining_days:
        return False, bal.remaining_days, (
            f"Insufficient balance: requested {days} day(s) of {leave_type.value} leave, "
            f"only {bal.remaining_days} remaining."
        )
    return True, bal.remaining_days, f"Balance OK: {bal.remaining_days} {leave_type.value} day(s) remaining."


def requires_human_approval(leave_type: LeaveType, days: int) -> tuple[bool, str]:
    """Deterministic approval-requirement rule."""
    if leave_type in ALWAYS_REQUIRES_APPROVAL:
        return True, "Earned leave always requires manager approval."
    if days > AUTO_APPROVE_MAX_DAYS:
        return True, f"Requests longer than {AUTO_APPROVE_MAX_DAYS} consecutive days require manager approval."
    return False, f"Within auto-approval limit ({days} day(s) of {leave_type.value} leave)."


def evaluate_and_create(
    db: Session,
    employee_id: str,
    leave_type: LeaveType,
    start: date,
    end: date,
    reason: str | None,
    policy_context: list | None = None,
    agent_notes: str | None = None,
    thread_id: str | None = None,
) -> tuple[LeaveRequest | None, str | None, dict]:
    """Full deterministic pipeline: validate -> balance -> approval rule -> create.

    Returns (leave_request, error, decision_info).
    decision_info keys: days, requires_approval, auto_approved, messages.
    """
    messages = []
    err = validate_dates(start, end)
    if err:
        return None, err, {}

    days = count_working_days(start, end)
    messages.append(f"{days} working day(s): {start} to {end}.")

    ok, remaining, msg = check_balance(db, employee_id, leave_type, days)
    messages.append(msg)
    if not ok:
        # rejected deterministically — but still record the request for audit
        lr = crud.create_leave_request(
            db, employee_id,
            leave_type=leave_type, start_date=start, end_date=end, days=days,
            reason=reason, status=LeaveStatus.REJECTED, requires_approval=False,
            policy_context=policy_context or [],
            agent_notes=msg, thread_id=thread_id,
        )
        return lr, None, {
            "days": days, "requires_approval": False, "auto_approved": False,
            "outcome": "REJECTED", "messages": messages,
        }

    needs_approval, why = requires_human_approval(leave_type, days)
    messages.append(why)

    if not needs_approval:
        # auto-approve: deterministic, consumes balance immediately
        lr = crud.create_leave_request(
            db, employee_id,
            leave_type=leave_type, start_date=start, end_date=end, days=days,
            reason=reason, status=LeaveStatus.PENDING, requires_approval=False,
            policy_context=policy_context or [],
            agent_notes=agent_notes or " | ".join(messages), thread_id=thread_id,
        )
        lr = crud.decide_leave_request(db, lr.id, approve=True, decided_by="AutoApproval")
        return lr, None, {
            "days": days, "requires_approval": False, "auto_approved": True,
            "outcome": "APPROVED", "messages": messages,
        }

    # needs human approval -> stay PENDING
    lr = crud.create_leave_request(
        db, employee_id,
        leave_type=leave_type, start_date=start, end_date=end, days=days,
        reason=reason, status=LeaveStatus.PENDING, requires_approval=True,
        policy_context=policy_context or [],
        agent_notes=agent_notes or " | ".join(messages), thread_id=thread_id,
    )
    return lr, None, {
        "days": days, "requires_approval": True, "auto_approved": False,
        "outcome": "PENDING_APPROVAL", "messages": messages,
    }
