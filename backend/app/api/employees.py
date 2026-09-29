"""Employee endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_hr
from app.api.schemas import (
    EmployeeCreate,
    EmployeeCreated,
    EmployeeDetail,
    EmployeeOut,
    LoginRoleUpdate,
    RolePreview,
    UserOut,
)
from app.config import settings
from app.db import crud
from app.db.database import get_db
from app.db.models import LeaveRequest, Meeting, OnboardingTask, Role, User
from app.security import (
    EMAIL_ROLE_PREFIXES,
    describe_role_prefix,
    email_role_prefix,
    hash_password,
    role_from_email,
)

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeOut])
def list_employees(db: Session = Depends(get_db), user: User = Depends(require_hr)):
    """HR only. Employees/managers use /api/me/* and /api/team."""
    return crud.list_employees(db)


@router.post("", response_model=EmployeeCreated, status_code=201)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db),
                    user: User = Depends(require_hr)):
    """Create an employee *and* a login for them.

    The access role is derived from the email prefix (see
    `app.security.role_from_email`), so the email HR types is what decides
    whether the new account is an employee, a manager, or HR.
    """
    data = payload.model_dump(exclude_none=True)
    if "skills" not in data:
        data["skills"] = []
    email = data["email"].strip().lower()
    if crud.get_employee_by_email(db, email) or crud.get_user_by_email(db, email):
        raise HTTPException(409, "An employee with this email already exists.")
    data["email"] = email

    # Reject a prefix that isn't a recognised role rather than silently
    # creating a less-privileged account than the HR admin intended.
    requested_role = Role(payload.login_role) if payload.login_role else None
    derived = role_from_email(email)
    if requested_role is None:
        prefix = email_role_prefix(email)
        if prefix and prefix not in EMAIL_ROLE_PREFIXES:
            raise HTTPException(
                422,
                f"'{prefix}' is not a recognised role prefix. Use one of: "
                f"{', '.join(sorted(EMAIL_ROLE_PREFIXES))} — or pass an explicit login_role.",
            )
        role = derived
    else:
        role = requested_role

    emp = crud.create_employee(db, data)
    crud.default_leave_balances(db, emp.id)
    account = crud.create_user(
        db,
        email=email,
        name=payload.login_name or emp.name,
        hashed_password=hash_password(payload.login_password or settings.demo_password),
        role=role,
        employee_id=emp.id,
    )
    crud.log_agent(
        db, "API", "employee_created", employee_id=emp.id,
        detail=f"Manual creation of {emp.name} ({emp.role}) by {user.name}. "
               f"Login {account.email} created with role {role.value} "
               f"({describe_role_prefix(email)}).",
    )
    return EmployeeCreated(
        **EmployeeOut.model_validate(emp).model_dump(),
        login_email=account.email,
        login_role=role.value,
        role_source="explicit" if requested_role else "email_prefix",
        role_reason=describe_role_prefix(email),
        default_password=payload.login_password is None,
    )


@router.get("/role-preview", response_model=RolePreview)
def preview_role(email: str, user: User = Depends(require_hr)):
    """What role would this email get? Lets the UI show it while HR is typing."""
    role = role_from_email(email)
    prefix = email_role_prefix(email)
    return RolePreview(
        email=email,
        prefix=prefix,
        role=role.value,
        recognized=bool(prefix and prefix in EMAIL_ROLE_PREFIXES),
        reason=describe_role_prefix(email),
    )


@router.patch("/{employee_id}/role", response_model=UserOut)
def set_employee_role(employee_id: str, payload: LoginRoleUpdate, db: Session = Depends(get_db),
                      user: User = Depends(require_hr)):
    """HR overrides the role of an existing user's login."""
    emp = crud.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(404, f"Employee {employee_id} not found.")
    acct = crud.get_user_by_email(db, emp.email)
    if not acct:
        raise HTTPException(404, f"No login account exists for {emp.email}.")
    previous = acct.role.value
    acct.role = Role(payload.role)
    db.commit()
    db.refresh(acct)
    crud.log_agent(
        db, "API", "role_changed", employee_id=emp.id,
        detail=f"Role for {emp.email} changed {previous} -> {Role(payload.role).value} by {user.name}.",
    )
    return UserOut.model_validate(acct)


@router.get("/{employee_id}", response_model=EmployeeDetail)
def get_employee(employee_id: str, db: Session = Depends(get_db),
                 user: User = Depends(require_hr)):
    emp = crud.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(404, f"Employee {employee_id} not found.")
    # Validate base fields only — avoid from_attributes picking up ORM relationships
    base = EmployeeOut.model_validate(emp).model_dump()
    detail = EmployeeDetail(**base)
    detail.progress = crud.employee_progress(db, employee_id)
    detail.tasks = [_task_out(t, emp.name) for t in crud.list_tasks(db, employee_id)]
    detail.meetings = [_meeting_out(m, emp.name) for m in crud.list_meetings(db, employee_id)]
    detail.leave_requests = [_leave_out(l, emp.name) for l in crud.list_leave_requests(db, employee_id)]
    detail.balances = [
        {"id": b.id, "employee_id": b.employee_id, "leave_type": b.leave_type.value,
         "total_days": b.total_days, "used_days": b.used_days,
         "remaining_days": b.remaining_days}
        for b in crud.list_balances(db, employee_id)
    ]  # dicts validate against BalanceOut
    return detail


@router.post("/{employee_id}/reset-password", response_model=EmployeeOut)
def reset_employee_password(employee_id: str, db: Session = Depends(get_db),
                            user: User = Depends(require_hr)):
    """HR resets an employee's login password to the demo password."""
    emp = crud.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(404, f"Employee {employee_id} not found.")
    acct = crud.get_user_by_email(db, emp.email)
    if not acct:
        raise HTTPException(404, f"No login account exists for {emp.email}.")
    acct.hashed_password = hash_password(settings.demo_password)
    db.commit()
    crud.log_agent(db, "API", "password_reset", employee_id=emp.id,
                   detail=f"Password reset for {emp.email} by {user.name}.")
    return emp


def _task_out(t: OnboardingTask, name: str) -> dict:
    d = {c.name: getattr(t, c.name) for c in t.__table__.columns}
    d["status"] = t.status.value
    d["employee_name"] = name
    return d


def _meeting_out(m: Meeting, name: str) -> dict:
    d = {c.name: getattr(m, c.name) for c in m.__table__.columns}
    d["status"] = m.status.value
    d["employee_name"] = name
    return d


def _leave_out(l: LeaveRequest, name: str) -> dict:
    d = {c.name: getattr(l, c.name) for c in l.__table__.columns}
    d["status"] = l.status.value
    d["leave_type"] = l.leave_type.value
    d["employee_name"] = name
    return d
