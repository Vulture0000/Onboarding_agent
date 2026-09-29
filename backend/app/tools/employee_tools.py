"""Employee tools: deterministic profile creation used by the Resume Agent."""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.db import crud
from app.db.models import Employee


def create_employee_profile(db: Session, info: dict, joining_date: date | None = None) -> Employee:
    """Create employee + default leave balances from extracted resume info.

    `info` comes from the Resume Agent's structured extraction. Deterministic
    normalization happens here — never in the LLM.
    """
    existing = crud.get_employee_by_email(db, info["email"]) if info.get("email") else None
    if existing:
        return existing

    emp = crud.create_employee(
        db,
        {
            "name": info["name"],
            "email": info.get("email") or f"{info['name'].lower().replace(' ', '.')}@example.com",
            "phone": info.get("phone"),
            "role": info.get("role") or "Software Engineer",
            "department": info.get("department") or "Engineering",
            "experience": info.get("experience") or "Fresher",
            "education": info.get("education"),
            "skills": info.get("skills") or [],
            "joining_date": joining_date or date.today(),
            "status": "ONBOARDING",
            "manager": info.get("manager"),
            "mentor": info.get("mentor"),
        },
    )
    crud.default_leave_balances(db, emp.id)
    return emp


def assign_manager_and_mentor(db: Session, emp: Employee) -> Employee:
    """Simple deterministic rule: pick an existing employee from the same
    department as manager, and a senior peer as mentor."""
    if emp.manager and emp.mentor:
        return emp
    peers = [
        e for e in crud.list_employees(db)
        if e.id != emp.id and e.department == emp.department and e.status == "ACTIVE"
    ]
    if not emp.manager:
        emp.manager = peers[0].name if peers else "Priya Sharma"
    if not emp.mentor:
        emp.mentor = peers[-1].name if len(peers) > 1 else (peers[0].name if peers else "Rahul Verma")
    db.commit()
    db.refresh(emp)
    return emp
