"""Resume Agent: turns an uploaded resume into a stored employee profile.

Pipeline: PDF text -> structured extraction (Gemini, heuristic fallback)
-> employee profile in SQLite. It does NOT make hiring decisions.
"""
from __future__ import annotations

import logging

from app.db import crud
from app.db.database import SessionLocal
from app.graph.state import OnboardingState
from app.tools import employee_tools
from app.tools.resume_tools import extract_structured_info

logger = logging.getLogger(__name__)


def resume_agent_node(state: OnboardingState) -> dict:
    db = SessionLocal()
    try:
        resume_data = dict(state.get("resume_data") or {})
        resume_id = state.get("resume_file_id")
        extraction_method = resume_data.pop("_method", "llm") if resume_data else "llm"

        # If raw text was supplied without structured data, extract now
        if not resume_data.get("name"):
            text = resume_data.get("_text") or ""
            if resume_id:
                r = db.get(crud.Resume, resume_id)
                if r and r.extracted_text:
                    text = r.extracted_text
            resume_data, extraction_method = extract_structured_info(text)

        if not resume_data.get("name"):
            crud.log_agent(db, "ResumeAgent", "extraction_failed",
                           status="error", detail="Could not extract a name from the resume.")
            return {"current_agent": "resume_agent",
                    "error": "Could not extract employee information from this resume."}

        # Reject duplicate emails deterministically
        if resume_data.get("email"):
            existing = crud.get_employee_by_email(db, resume_data["email"])
            if existing:
                crud.log_agent(db, "ResumeAgent", "duplicate_employee",
                               employee_id=existing.id, status="warning",
                               detail=f"Employee with email {resume_data['email']} already exists.")
                messages = list(state.get("messages") or [])
                messages.append({
                    "role": "assistant", "agent": "ResumeAgent",
                    "content": f"An employee with email {resume_data['email']} already exists ({existing.id}).",
                })
                return {
                    "current_agent": "resume_agent",
                    "employee_id": existing.id,
                    "resume_data": resume_data,
                    "employee_data": {"id": existing.id, "name": existing.name},
                    "messages": messages,
                    "error": f"Employee with this email already exists: {existing.id}",
                }

        # Create (or fetch) the resume record and the employee profile
        if resume_id:
            r = db.get(crud.Resume, resume_id)
            if r:
                r.extracted_data = resume_data
                r.extraction_method = extraction_method
                db.commit()

        emp = employee_tools.create_employee_profile(db, resume_data)
        emp = employee_tools.assign_manager_and_mentor(db, emp)

        if resume_id:
            r = db.get(crud.Resume, resume_id)
            if r:
                r.employee_id = emp.id
                db.commit()

        crud.log_agent(
            db, "ResumeAgent", "resume_processed", employee_id=emp.id,
            detail=f"Extracted profile for {emp.name} ({emp.role}, {emp.department}) via {extraction_method}.",
        )
        messages = list(state.get("messages") or [])
        messages.append({
            "role": "assistant", "agent": "ResumeAgent",
            "content": f"Created employee profile {emp.id} for {emp.name} "
                       f"({emp.role}, {emp.department}) using {extraction_method} extraction.",
        })
        return {
            "current_agent": "resume_agent",
            "employee_id": emp.id,
            "resume_data": resume_data,
            "employee_data": {
                "id": emp.id, "name": emp.name, "email": emp.email, "role": emp.role,
                "department": emp.department, "manager": emp.manager, "mentor": emp.mentor,
                "experience": emp.experience, "joining_date": emp.joining_date.isoformat(),
            },
            "messages": messages,
            "result": {"employee_id": emp.id, "resume_data": resume_data,
                       "extraction_method": extraction_method},
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("ResumeAgent failed")
        crud.log_agent(db, "ResumeAgent", "agent_error", status="error", detail=str(exc))
        return {"current_agent": "resume_agent", "error": f"ResumeAgent failed: {exc}"}
    finally:
        db.close()
