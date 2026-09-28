"""Supervisor / Orchestrator: classifies the request and routes to the right agent.

Routing is deterministic when the API already knows the workflow
(state["request_type"]); the LLM is only used to classify free-text messages,
with a keyword fallback so routing works without the LLM (Rule 7).
"""
from __future__ import annotations

import logging

from app.agents.llm import llm_complete
from app.db.database import SessionLocal
from app.db import crud
from app.graph.state import OnboardingState

logger = logging.getLogger(__name__)

VALID_ROUTES = {"resume_agent", "onboarding_agent", "calendar_agent", "leave_agent", "policy_agent", "end"}

CLASSIFY_PROMPT = """You are a routing supervisor for an employee onboarding system.
Classify the user request into exactly ONE of these categories:

- resume: uploading/parsing a resume, creating an employee profile from a resume
- leave: requesting time off, leave balance questions tied to a specific request, cancelling leave
- meeting: scheduling, rescheduling, listing or cancelling onboarding meetings
- policy: questions about company HR policies (leave rules, attendance, WFH, security, onboarding policy)
- onboarding: questions about onboarding tasks/progress or generating an onboarding plan
- general: anything else

Respond with ONLY the category name, nothing else.

Request: {message}"""

KEYWORD_ROUTES = [
    (("resume", "cv", "pdf", "upload", "candidate"), "resume"),
    (("leave", "time off", "vacation", "day off", "casual", "sick leave", "earned leave"), "leave"),
    (("meeting", "schedule", "calendar", "reschedule", "1:1", "orientation"), "meeting"),
    (("policy", "policies", "rule", "allowed", "entitle", "how many", "wfh", "work from home",
      "attendance", "probation", "security training", "handbook"), "policy"),
    (("onboard", "task", "checklist", "progress", "to-do", "todo"), "onboarding"),
]

CATEGORY_TO_AGENT = {
    "resume": "resume_agent",
    "leave": "leave_agent",
    "meeting": "calendar_agent",
    "policy": "policy_agent",
    "onboarding": "onboarding_agent",
    "general": "policy_agent",  # free-text default: answer from HR policies
}


def _classify_by_keywords(message: str) -> str:
    low = message.lower()
    for keywords, category in KEYWORD_ROUTES:
        if any(k in low for k in keywords):
            return category
    return "general"


def classify_intent(message: str) -> str:
    """Classify free-text into a category. LLM first, keyword fallback."""
    result = llm_complete(CLASSIFY_PROMPT.format(message=message[:1000]))
    if result:
        cat = result.strip().lower().split()[0] if result.strip() else ""
        if cat in CATEGORY_TO_AGENT:
            return cat
    return _classify_by_keywords(message)


def supervisor_node(state: OnboardingState) -> dict:
    """Decide the next agent and record the routing decision."""
    db = SessionLocal()
    try:
        request_type = state.get("request_type")
        message = state.get("user_message", "")

        if request_type in ("resume", "leave", "meeting", "policy", "onboarding"):
            category = request_type
        elif message:
            category = classify_intent(message)
        else:
            category = "general"

        next_agent = CATEGORY_TO_AGENT.get(category, "policy_agent")

        crud.log_agent(
            db, "Supervisor", "route_request",
            employee_id=state.get("employee_id"),
            detail=f"category={category} -> {next_agent}",
        )
        messages = list(state.get("messages") or [])
        messages.append({
            "role": "assistant",
            "agent": "Supervisor",
            "content": f"Routing request ({category}) to {next_agent}.",
        })
        return {
            "current_agent": "supervisor",
            "next_agent": next_agent,
            "request_type": category,
            "messages": messages,
        }
    finally:
        db.close()


def route_from_supervisor(state: OnboardingState) -> str:
    """Conditional edge: where should the graph go after the supervisor?"""
    if state.get("error"):
        return "end"
    nxt = state.get("next_agent")
    return nxt if nxt in VALID_ROUTES else "policy_agent"
