"""CRUD helpers. All database writes for agents go through here (deterministic code)."""
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AgentLog,
    Employee,
    LeaveBalance,
    LeaveRequest,
    LeaveStatus,
    LeaveType,
    Meeting,
    MeetingStatus,
    OnboardingTask,
    Resume,
    Role,
    TaskStatus,
    User,
)

# --------------------------------------------------------------------------- #
# Agent logging
# --------------------------------------------------------------------------- #

def log_agent(
    db: Session,
    agent: str,
    action: str,
    employee_id: str | None = None,
    status: str = "completed",
    detail: str | None = None,
) -> AgentLog:
    entry = AgentLog(
        agent=agent,
        action=action,
        employee_id=employee_id,
        status=status,
        detail=detail,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_agent_logs(db: Session, limit: int = 100, user: User | None = None) -> list[AgentLog]:
    q = select(AgentLog).order_by(AgentLog.timestamp.desc(), AgentLog.id.desc())
    if user is not None:
        q = apply_scope(q, AgentLog.employee_id, user, db)
    return list(db.scalars(q.limit(limit)))


# --------------------------------------------------------------------------- #
# Users / auth
# --------------------------------------------------------------------------- #

def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))


def create_user(
    db: Session, email: str, name: str, hashed_password: str, role: Role,
    employee_id: str | None = None,
) -> User:
    user = User(
        email=email.strip().lower(),
        name=name,
        hashed_password=hashed_password,
        role=role,
        employee_id=employee_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def count_users(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(User)) or 0


# --------------------------------------------------------------------------- #
# Employees
# --------------------------------------------------------------------------- #

def team_employee_ids(db: Session, manager_id: str) -> list[str]:
    """Employee ids reporting to this manager."""
    return list(
        db.scalars(
            select(Employee.id)
            .where(Employee.manager_id == manager_id)
            .order_by(Employee.id)
        )
    )


def visible_employee_ids(db: Session, user: User) -> list[str] | None:
    """Employee ids a user may read.

    Returns None for "unrestricted" (HR sees everything). MANAGER sees their team,
    EMPLOYEE sees only themselves.
    """
    if user.role == Role.HR:
        return None
    if user.role == Role.MANAGER and user.employee_id:
        return team_employee_ids(db, user.employee_id)
    return [user.employee_id] if user.employee_id else []


def can_access_employee(db: Session, user: User, employee_id: str) -> bool:
    visible = visible_employee_ids(db, user)
    return visible is None or employee_id in visible


def apply_scope(stmt, column, user: User, db: Session):
    """Restrict a select statement to the employees the user may see."""
    visible = visible_employee_ids(db, user)
    if visible is None:
        return stmt
    if not visible:
        return stmt.where(column.is_(None))  # matches nothing, including NULLs
    return stmt.where(column.in_(visible))


def next_employee_id(db: Session) -> str:
    count = db.scalar(select(func.count()).select_from(Employee)) or 0
    # avoid collisions with existing ids
    while True:
        count += 1
        emp_id = f"EMP{count:03d}"
        if not db.get(Employee, emp_id):
            return emp_id


def create_employee(db: Session, data: dict) -> Employee:
    emp = Employee(
        id=data.get("employee_id") or next_employee_id(db),
        name=data["name"],
        email=data["email"],
        phone=data.get("phone"),
        role=data.get("role"),
        department=data.get("department"),
        manager=data.get("manager"),
        manager_id=data.get("manager_id"),
        mentor=data.get("mentor"),
        experience=data.get("experience"),
        education=data.get("education"),
        skills=data.get("skills") or [],
        joining_date=data.get("joining_date") or date.today(),
        status=data.get("status", "ONBOARDING"),
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


def get_employee(db: Session, employee_id: str) -> Employee | None:
    return db.get(Employee, employee_id)


def get_employee_by_email(db: Session, email: str) -> Employee | None:
    return db.scalar(select(Employee).where(func.lower(Employee.email) == email.lower()))


def list_employees(db: Session, user: User | None = None) -> list[Employee]:
    q = select(Employee).order_by(Employee.created_at.desc())
    if user is not None:
        q = apply_scope(q, Employee.id, user, db)
    return list(db.scalars(q))


# Entitlements per calendar year, taken from data/policies/leave_policy.txt
# ("LEAVE ENTITLEMENTS"). These must stay in sync with the policy document:
# the balance check rejects any request that exceeds the available days, so a
# zero default made every leave request fail and left the seeded data
# contradicting the policy the system claims to enforce.
POLICY_ENTITLEMENTS: dict[LeaveType, int] = {
    LeaveType.CASUAL: 8,
    LeaveType.SICK: 10,
    LeaveType.EARNED: 12,
}

# Policy: "Employees on probation (first 3 months) may use casual and sick
# leave only", so earned leave is withheld until probation ends.
PROBATION_MONTHS = 3


def _months_since(d: date | None) -> int | None:
    if not d:
        return None
    today = date.today()
    return (today.year - d.year) * 12 + (today.month - d.month)


def default_leave_balances(db: Session, employee_id: str) -> list[LeaveBalance]:
    """Create annual leave balances for a new employee.

    Entitlements follow the policy document. Earned leave is withheld while the
    employee is within their probation period.
    """
    emp = db.get(Employee, employee_id)
    in_probation = False
    months = _months_since(emp.joining_date) if emp else None
    if months is not None:
        in_probation = months < PROBATION_MONTHS

    balances = []
    for ltype, total in POLICY_ENTITLEMENTS.items():
        if ltype is LeaveType.EARNED and in_probation:
            total = 0
        b = LeaveBalance(
            employee_id=employee_id,
            leave_type=ltype,
            total_days=total,
            used_days=0,
            year=datetime.now().year,
        )
        db.add(b)
        balances.append(b)
    db.commit()
    return balances


# --------------------------------------------------------------------------- #
# Resumes
# --------------------------------------------------------------------------- #

def create_resume(db: Session, **kwargs) -> Resume:
    r = Resume(**kwargs)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def list_resumes(db: Session) -> list[Resume]:
    return list(db.scalars(select(Resume).order_by(Resume.created_at.desc())))


# --------------------------------------------------------------------------- #
# Onboarding tasks
# --------------------------------------------------------------------------- #

def create_task(db: Session, employee_id: str, **kwargs) -> OnboardingTask:
    t = OnboardingTask(employee_id=employee_id, **kwargs)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def bulk_create_tasks(db: Session, employee_id: str, tasks: list[dict]) -> list[OnboardingTask]:
    objs = [OnboardingTask(employee_id=employee_id, **t) for t in tasks]
    db.add_all(objs)
    db.commit()
    for o in objs:
        db.refresh(o)
    return objs


def list_tasks(
    db: Session,
    employee_id: str | None = None,
    status: str | None = None,
    user: User | None = None,
) -> list[OnboardingTask]:
    q = select(OnboardingTask).order_by(OnboardingTask.due_date.asc(), OnboardingTask.id.asc())
    if employee_id:
        q = q.where(OnboardingTask.employee_id == employee_id)
    if user is not None:
        q = apply_scope(q, OnboardingTask.employee_id, user, db)
    if status:
        q = q.where(OnboardingTask.status == TaskStatus(status))
    return list(db.scalars(q))


def update_task_status(db: Session, task_id: int, status: TaskStatus) -> OnboardingTask | None:
    t = db.get(OnboardingTask, task_id)
    if not t:
        return None
    t.status = status
    db.commit()
    db.refresh(t)
    return t


def refresh_overdue_tasks(db: Session) -> int:
    """Mark non-completed tasks past their due date as OVERDUE (deterministic rule)."""
    today = date.today()
    tasks = db.scalars(
        select(OnboardingTask).where(
            OnboardingTask.due_date < today,
            OnboardingTask.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS]),
        )
    ).all()
    for t in tasks:
        t.status = TaskStatus.OVERDUE
    if tasks:
        db.commit()
    return len(tasks)


def employee_progress(db: Session, employee_id: str) -> dict:
    total = db.scalar(
        select(func.count()).select_from(OnboardingTask).where(OnboardingTask.employee_id == employee_id)
    ) or 0
    done = db.scalar(
        select(func.count())
        .select_from(OnboardingTask)
        .where(OnboardingTask.employee_id == employee_id, OnboardingTask.status == TaskStatus.COMPLETED)
    ) or 0
    pct = round(done / total * 100) if total else 0
    return {"total_tasks": total, "completed_tasks": done, "progress_pct": pct}


# --------------------------------------------------------------------------- #
# Meetings
# --------------------------------------------------------------------------- #

def create_meeting(db: Session, employee_id: str, **kwargs) -> Meeting:
    m = Meeting(employee_id=employee_id, **kwargs)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def bulk_create_meetings(db: Session, meetings: list[dict]) -> list[Meeting]:
    objs = [Meeting(**m) for m in meetings]
    db.add_all(objs)
    db.commit()
    for o in objs:
        db.refresh(o)
    return objs


def list_meetings(
    db: Session,
    employee_id: str | None = None,
    upcoming_only: bool = False,
    user: User | None = None,
) -> list[Meeting]:
    q = select(Meeting).order_by(Meeting.date.asc(), Meeting.start_time.asc())
    if employee_id:
        q = q.where(Meeting.employee_id == employee_id)
    if user is not None:
        q = apply_scope(q, Meeting.employee_id, user, db)
    if upcoming_only:
        q = q.where(Meeting.date >= date.today(), Meeting.status == MeetingStatus.SCHEDULED)
    return list(db.scalars(q))


def get_meeting(db: Session, meeting_id: int) -> Meeting | None:
    return db.get(Meeting, meeting_id)


def update_meeting(db: Session, meeting_id: int, **fields) -> Meeting | None:
    m = db.get(Meeting, meeting_id)
    if not m:
        return None
    for k, v in fields.items():
        if v is not None and hasattr(m, k):
            setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return m


def meetings_on_slot(db: Session, day: date, start: str, end: str, exclude_id: int | None = None) -> list[Meeting]:
    q = select(Meeting).where(
        Meeting.date == day,
        Meeting.status == MeetingStatus.SCHEDULED,
        Meeting.start_time < end,
        Meeting.end_time > start,
    )
    if exclude_id:
        q = q.where(Meeting.id != exclude_id)
    return list(db.scalars(q))


# --------------------------------------------------------------------------- #
# Leave
# --------------------------------------------------------------------------- #

def get_balance(db: Session, employee_id: str, leave_type: LeaveType) -> LeaveBalance | None:
    return db.scalar(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_type == leave_type,
            LeaveBalance.year == datetime.now().year,
        )
    )


def list_balances(db: Session, employee_id: str | None = None, user: User | None = None) -> list[LeaveBalance]:
    q = select(LeaveBalance)
    if employee_id:
        q = q.where(LeaveBalance.employee_id == employee_id)
    if user is not None:
        q = apply_scope(q, LeaveBalance.employee_id, user, db)
    return list(db.scalars(q))


def create_leave_request(db: Session, employee_id: str, **kwargs) -> LeaveRequest:
    lr = LeaveRequest(employee_id=employee_id, **kwargs)
    db.add(lr)
    db.commit()
    db.refresh(lr)
    return lr


def get_leave_request(db: Session, leave_id: int) -> LeaveRequest | None:
    return db.get(LeaveRequest, leave_id)


def list_leave_requests(
    db: Session,
    employee_id: str | None = None,
    status: str | None = None,
    user: User | None = None,
) -> list[LeaveRequest]:
    q = select(LeaveRequest).order_by(LeaveRequest.created_at.desc())
    if employee_id:
        q = q.where(LeaveRequest.employee_id == employee_id)
    if user is not None:
        q = apply_scope(q, LeaveRequest.employee_id, user, db)
    if status:
        q = q.where(LeaveRequest.status == LeaveStatus(status))
    return list(db.scalars(q))


def decide_leave_request(
    db: Session, leave_id: int, approve: bool, decided_by: str = "HR Admin"
) -> LeaveRequest | None:
    """Deterministic status transition + balance update. Never delegated to the LLM."""
    lr = db.get(LeaveRequest, leave_id)
    if not lr or lr.status != LeaveStatus.PENDING:
        return None
    lr.status = LeaveStatus.APPROVED if approve else LeaveStatus.REJECTED
    lr.decided_by = decided_by
    lr.decided_at = datetime.now(timezone.utc)
    if approve:
        bal = get_balance(db, lr.employee_id, lr.leave_type)
        if bal:
            bal.used_days += lr.days
    db.commit()
    db.refresh(lr)
    return lr


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #

def dashboard_stats(db: Session, user: User | None = None) -> dict:
    """Org-wide aggregates, or team-wide ones when a user scope is supplied."""
    emp_q = select(func.count()).select_from(Employee)
    onboarding_q = select(func.count()).select_from(Employee).where(Employee.status == "ONBOARDING")
    tasks_done_q = select(func.count()).select_from(OnboardingTask).where(
        OnboardingTask.status == TaskStatus.COMPLETED
    )
    tasks_total_q = select(func.count()).select_from(OnboardingTask)
    meetings_q = select(func.count()).select_from(Meeting).where(
        Meeting.date >= date.today(), Meeting.status == MeetingStatus.SCHEDULED
    )
    pending_q = select(func.count()).select_from(LeaveRequest).where(
        LeaveRequest.status == LeaveStatus.PENDING
    )

    if user is not None:
        emp_q = apply_scope(emp_q, Employee.id, user, db)
        onboarding_q = apply_scope(onboarding_q, Employee.id, user, db)
        tasks_done_q = apply_scope(tasks_done_q, OnboardingTask.employee_id, user, db)
        tasks_total_q = apply_scope(tasks_total_q, OnboardingTask.employee_id, user, db)
        meetings_q = apply_scope(meetings_q, Meeting.employee_id, user, db)
        pending_q = apply_scope(pending_q, LeaveRequest.employee_id, user, db)

    return {
        "employees": db.scalar(emp_q) or 0,
        "onboarding": db.scalar(onboarding_q) or 0,
        "upcoming_meetings": db.scalar(meetings_q) or 0,
        "pending_leave": db.scalar(pending_q) or 0,
        "tasks_completed": db.scalar(tasks_done_q) or 0,
        "tasks_total": db.scalar(tasks_total_q) or 0,
    }
