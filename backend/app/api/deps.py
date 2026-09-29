"""Authentication + authorization dependencies.

`get_current_user` resolves the JWT into a User row. `require_roles` gates whole
endpoints by role. `can_view_employee` / `assert_can_view_employee` apply the
row-level scope (HR = everyone, MANAGER = own team, EMPLOYEE = self).
"""
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db import crud
from app.db.database import get_db
from app.db.models import Role, User
from app.security import decode_access_token

_UNAUTH = "Not authenticated. Please sign in."


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the bearer token to an active User, or 401."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _UNAUTH)
    claims = decode_access_token(authorization.split(" ", 1)[1].strip())
    if not claims:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Session expired or invalid. Please sign in again."
        )
    user = crud.get_user(db, int(claims["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account is inactive.")
    return user


def require_roles(*roles: Role):
    """Dependency factory: allow only the listed roles."""

    allowed = {r.value for r in roles}

    def _guard(user: User = Depends(get_current_user)) -> User:
        if user.role.value not in allowed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"This action requires one of: {', '.join(sorted(allowed))}.",
            )
        return user

    return _guard


require_hr = require_roles(Role.HR)
require_manager = require_roles(Role.HR, Role.MANAGER)
require_manager_or_self = require_roles(Role.HR, Role.MANAGER, Role.EMPLOYEE)


def can_view_employee(db: Session, user: User, employee_id: str) -> bool:
    return crud.can_access_employee(db, user, employee_id)


def assert_can_view_employee(db: Session, user: User, employee_id: str) -> None:
    if not can_view_employee(db, user, employee_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You do not have access to this employee's records.",
        )


def assert_can_decide_leave(db: Session, user: User, leave_employee_id: str) -> None:
    """Approving/rejecting is a manager-or-HR action, scoped to their own team."""
    if user.role == Role.HR:
        return
    if user.role == Role.MANAGER and crud.can_access_employee(db, user, leave_employee_id):
        return
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        "Only the employee's reporting manager or HR can decide this request.",
    )