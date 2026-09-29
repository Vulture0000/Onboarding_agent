"""Shared LangGraph state — the single communication channel between agents (Rule 4)."""
from typing import Any, TypedDict


class OnboardingState(TypedDict, total=False):
    # Request routing
    request_type: str            # resume | leave | policy | meeting | general
    user_message: str

    # Identity / profile
    employee_id: str
    employee_data: dict
    resume_data: dict
    resume_file_id: int

    # Onboarding
    onboarding_tasks: list       # generated task dicts (as created)
    completed_tasks: list

    # Calendar
    meetings: list               # generated meeting dicts

    # Leave
    leave_request: dict          # parsed request {employee_id, leave_type, start_date, end_date, reason}
    leave_phase: str             # intake | decide
    leave_result: dict           # deterministic decision info from leave_tools
    leave_status: str            # PENDING | APPROVED | REJECTED
    requires_human_approval: bool
    human_decision: str          # approve | reject (set on resume)
    human_decided_by: str        # display name of the approver who made the decision

    # Policy / RAG
    policy_question: str
    policy_context: list         # retrieved chunks [{source, content, score}]
    policy_answer: str

    # Orchestration
    messages: list               # [{role, content, agent}]
    current_agent: str
    next_agent: str
    error: str
    result: dict[str, Any]       # final API-facing summary
