"""Onboarding Agent: generates a role-aware onboarding plan and stores every
task in SQLite. Task generation is deterministic (template + role/department
rules); the LLM is not used for critical business logic (Rule 2).
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from app.db import crud
from app.db.database import SessionLocal
from app.graph.state import OnboardingState
from app.tools.calendar_tools import next_workday

logger = logging.getLogger(__name__)

# Base plan every new hire gets: (title, description, category, priority, due_offset_days)
COMMON_PLAN = [
    ("Complete HR documentation", "Sign offer letter, submit ID proofs, bank details and emergency contacts.", "HR", "HIGH", 1),
    ("Complete security training", "Finish the mandatory information security and data privacy module.", "Compliance", "HIGH", 2),
    ("Setup laptop", "Collect device from IT and complete initial configuration.", "IT", "HIGH", 1),
    ("Meet manager", "Introductory 1:1 with the reporting manager.", "People", "HIGH", 2),
    ("Meet team", "Team introduction session.", "People", "MEDIUM", 3),
    ("Meet mentor", "Kickoff meeting with the assigned onboarding buddy.", "People", "MEDIUM", 3),
]

ROLE_PLANS = {
    "Engineering": [
        ("Setup Git", "Create Git account, add SSH keys, request repository access.", "IT", "MEDIUM", 3),
        ("Setup development environment", "Install required tooling and clone primary repositories.", "Engineering", "MEDIUM", 4),
        ("Read engineering handbook", "Go through coding standards, review process and on-call policy.", "Engineering", "LOW", 5),
        ("Complete first technical task", "Pick up a starter ticket and ship it through code review.", "Engineering", "MEDIUM", 10),
    ],
    "Data": [
        ("Setup analytics tools", "Get access to the data warehouse, BI tools and notebook environment.", "IT", "MEDIUM", 3),
        ("Read data governance guide", "Understand data classification, privacy and query policies.", "Data", "MEDIUM", 5),
        ("Complete first analysis task", "Build a small dashboard or analysis for the team.", "Data", "MEDIUM", 10),
    ],
    "Design": [
        ("Setup design tools", "Get Figma access and review the design system library.", "IT", "MEDIUM", 3),
        ("Read design guidelines", "Go through brand, accessibility and design review process docs.", "Design", "LOW", 5),
        ("Complete first design task", "Take a small design brief through critique.", "Design", "MEDIUM", 10),
    ],
    "Human Resources": [
        ("Setup HRIS access", "Get access to the HR portal, payroll system and applicant tracker.", "IT", "MEDIUM", 3),
        ("Read HR manual", "Review employee handbook, leave policy and code of conduct.", "HR", "LOW", 5),
        ("Shadow an HR process", "Observe one recruitment or payroll cycle end to end.", "HR", "MEDIUM", 10),
    ],
    "_default": [
        ("Setup tools and access", "Request access to the tools your team uses daily.", "IT", "MEDIUM", 3),
        ("Read department handbook", "Go through your department's processes and guidelines.", "General", "LOW", 5),
        ("Complete first work task", "Deliver a small starter task with your manager's guidance.", "General", "MEDIUM", 10),
    ],
}


def build_plan(role: str | None, department: str | None, experience: str | None, joining: date) -> list[dict]:
    """Deterministic onboarding plan generation."""
    dept_plan = ROLE_PLANS.get((department or "").strip(), ROLE_PLANS["_default"])
    items = COMMON_PLAN + dept_plan

    # Experienced hires skip the most basic orientation reading
    is_fresher = not experience or "fresher" in experience.lower() or experience.strip() == "0"
    tasks = []
    for title, desc, cat, prio, offset in items:
        if not is_fresher and title == "Meet mentor":
            desc += " (Experienced hire: focus on network building.)"
        tasks.append({
            "title": title,
            "description": desc,
            "category": cat,
            "priority": prio,
            "due_date": next_workday(joining + timedelta(days=offset)),
            "status": "TODO",
        })
    return tasks


def onboarding_agent_node(state: OnboardingState) -> dict:
    db = SessionLocal()
    try:
        employee_id = state.get("employee_id")
        if not employee_id:
            return {"current_agent": "onboarding_agent",
                    "error": "OnboardingAgent needs an employee_id."}

        emp = crud.get_employee(db, employee_id)
        if not emp:
            return {"current_agent": "onboarding_agent",
                    "error": f"Employee {employee_id} not found."}

        existing = crud.list_tasks(db, employee_id=employee_id)
        if existing:
            crud.log_agent(db, "OnboardingAgent", "plan_exists", employee_id=employee_id,
                           status="warning", detail=f"{len(existing)} tasks already exist; skipped generation.")
            messages = list(state.get("messages") or [])
            messages.append({"role": "assistant", "agent": "OnboardingAgent",
                             "content": f"Onboarding plan already exists for {emp.name} ({len(existing)} tasks)."})
            progress = crud.employee_progress(db, employee_id)
            return {"current_agent": "onboarding_agent", "messages": messages,
                    "result": {**(state.get("result") or {}), "tasks": progress}}

        plan = build_plan(emp.role, emp.department, emp.experience, emp.joining_date)
        tasks = crud.bulk_create_tasks(db, employee_id, plan)

        crud.log_agent(db, "OnboardingAgent", "generate_plan", employee_id=employee_id,
                       detail=f"Generated {len(tasks)} onboarding tasks for {emp.role} in {emp.department}.")
        messages = list(state.get("messages") or [])
        messages.append({
            "role": "assistant", "agent": "OnboardingAgent",
            "content": f"Generated {len(tasks)} onboarding tasks for {emp.name} "
                       f"({emp.role}, {emp.department}, experience: {emp.experience or 'Fresher'}).",
        })
        return {
            "current_agent": "onboarding_agent",
            "onboarding_tasks": [
                {"id": t.id, "title": t.title, "status": t.status.value,
                 "priority": t.priority, "due_date": t.due_date.isoformat() if t.due_date else None}
                for t in tasks
            ],
            "messages": messages,
            "result": {**(state.get("result") or {}),
                       "tasks_generated": len(tasks)},
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("OnboardingAgent failed")
        crud.log_agent(db, "OnboardingAgent", "agent_error",
                       employee_id=state.get("employee_id"), status="error", detail=str(exc))
        return {"current_agent": "onboarding_agent", "error": f"OnboardingAgent failed: {exc}"}
    finally:
        db.close()
