"""Authentication endpoints: signup, login and current-session lookup."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.onboarding_agent import build_plan
from app.api.deps import get_current_user
from app.api.schemas import LoginRequest, LoginResponse, SignupRequest, UserOut
from app.db import crud
from app.db.database import get_db
from app.db.models import Role, User
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=LoginResponse, status_code=201)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    """Public registration. Always creates an EMPLOYEE account.

    Security notes:
      * The role is hardcoded to EMPLOYEE. It is never read from the request,
        so nobody can self-register as a manager or HR.
      * If HR already created an employee record with this email but no login,
        the signup attaches a login to that existing record instead of creating
        a duplicate person ("claim your account").
      * The password is hashed with the same PBKDF2 routine as login.
    """
    email = payload.email.strip().lower()

    if crud.get_user_by_email(db, email):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "An account with this email already exists. Sign in instead.",
        )

    existing = crud.get_employee_by_email(db, email)
    if existing:
        # HR created the person first; they are only claiming their login.
        employee_id = existing.id
        created_employee = False
    else:
        emp = crud.create_employee(
            db,
            {
                "name": payload.name.strip(),
                "email": email,
                "status": "ONBOARDING",
                "joining_date": date.today(),
            },
        )
        employee_id = emp.id
        created_employee = True
        # Deterministic onboarding plan, same generator the Onboarding Agent uses.
        crud.bulk_create_tasks(
            db, employee_id, build_plan(None, None, None, date.today())
        )
        crud.default_leave_balances(db, employee_id)

    user = crud.create_user(
        db,
        email=email,
        name=payload.name.strip(),
        hashed_password=hash_password(payload.password),
        role=Role.EMPLOYEE,  # hardcoded — never client-supplied
        employee_id=employee_id,
    )

    crud.log_agent(
        db, "System", "signup", employee_id=employee_id,
        detail=(
            f"{user.name} self-registered as EMPLOYEE"
            f"{' and was linked to the existing employee record' if not created_employee else ''}."
        ),
    )

    token = create_access_token(user.id, user.email, user.role.value, user.employee_id)
    return LoginResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, payload.email)
    # Same message for unknown email and wrong password — don't leak which emails exist.
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated.")

    token = create_access_token(user.id, user.email, user.role.value, user.employee_id)
    crud.log_agent(
        db, "System", "login", employee_id=user.employee_id,
        detail=f"{user.name} ({user.role.value}) signed in.",
    )
    return LoginResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/demo-accounts")
def demo_accounts(db: Session = Depends(get_db)):
    """Demo helper: list the seeded logins so the login screen can offer them."""
    accounts = db.query(User).order_by(User.id).all()
    return [
        {"email": u.email, "name": u.name, "role": u.role.value}
        for u in accounts
    ]