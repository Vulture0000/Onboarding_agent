"""Authentication endpoints: login and current-session lookup."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas import LoginRequest, LoginResponse, UserOut
from app.db import crud
from app.db.database import get_db
from app.db.models import User
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


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