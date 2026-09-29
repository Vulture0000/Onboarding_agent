"""Seed realistic demo data on first startup (only if DB is empty)."""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import crud
from app.db.models import (
    Employee,
    LeaveStatus,
    LeaveType,
    MeetingStatus,
    Role,
    TaskStatus,
)
from app.security import hash_password

# Demo login credentials (password is settings.demo_password, default Demo@1234).
DEMO_HR = {"email": "hr1000@xyzcorp.com", "name": "Meera Iyer"}
DEMO_MANAGER = {"email": "manage1234@xyzcorp.com", "name": "Priya Sharma"}
DEMO_EMPLOYEE = {"email": "employee1021@xyzcorp.com", "name": "Arun Kumar"}

SEED_EMPLOYEES = [
    {
        "key": "priya",
        "name": "Priya Sharma",
        "email": "manage1234@xyzcorp.com",
        "phone": "+91 90000 10001",
        "role": "Engineering Manager",
        "department": "Engineering",
        "manager": None,
        "manager_key": None,
        "mentor": None,
        "experience": "9 years",
        "education": "M.Tech Computer Science",
        "skills": ["Leadership", "System Design", "Python"],
        "join_offset": -400,
        "status": "ACTIVE",
    },
    {
        "key": "anil",
        "name": "Anil Menon",
        "email": "anil.menon@xyzcorp.com",
        "phone": "+91 90000 10002",
        "role": "Data Manager",
        "department": "Data",
        "manager": None,
        "manager_key": None,
        "mentor": None,
        "experience": "8 years",
        "education": "M.Tech Statistics",
        "skills": ["Analytics", "SQL", "Team Leadership"],
        "join_offset": -380,
        "status": "ACTIVE",
    },
    {
        "key": "arun",
        "name": "Arun Kumar",
        "email": "employee1021@xyzcorp.com",
        "phone": "+91 98765 43210",
        "role": "Software Engineer",
        "department": "Engineering",
        "manager": "Priya Sharma",
        "manager_key": "priya",
        "mentor": "Rahul Verma",
        "experience": "Fresher",
        "education": "B.E Computer Science",
        "skills": ["Python", "FastAPI", "React"],
        "join_offset": -12,
        "status": "ONBOARDING",
    },
    {
        "key": "sneha",
        "name": "Sneha Patel",
        "email": "sneha.patel@xyzcorp.com",
        "phone": "+91 99887 76655",
        "role": "Data Analyst",
        "department": "Data",
        "manager": "Anil Menon",
        "manager_key": "anil",
        "mentor": "Kavya Nair",
        "experience": "2 years",
        "education": "M.Sc Statistics",
        "skills": ["SQL", "Python", "Power BI"],
        "join_offset": -8,
        "status": "ONBOARDING",
    },
    {
        "key": "vikram",
        "name": "Vikram Singh",
        "email": "vikram.singh@xyzcorp.com",
        "phone": "+91 90909 80807",
        "role": "DevOps Engineer",
        "department": "Engineering",
        "manager": "Priya Sharma",
        "manager_key": "priya",
        "mentor": "Rahul Verma",
        "experience": "4 years",
        "education": "B.Tech Information Technology",
        "skills": ["Docker", "Kubernetes", "AWS", "Terraform"],
        "join_offset": -5,
        "status": "ONBOARDING",
    },
    {
        "key": "meera",
        "name": "Meera Iyer",
        "email": "hr1000@xyzcorp.com",
        "phone": "+91 91234 56789",
        "role": "HR Executive",
        "department": "Human Resources",
        "manager": None,
        "manager_key": None,
        "mentor": None,
        "experience": "3 years",
        "education": "MBA Human Resources",
        "skills": ["Recruitment", "Payroll", "Employee Relations"],
        "join_offset": -200,
        "status": "ACTIVE",
    },
    {
        "key": "daniel",
        "name": "Daniel Fernandes",
        "email": "daniel.fernandes@xyzcorp.com",
        "phone": "+91 98123 45670",
        "role": "Product Designer",
        "department": "Design",
        "manager": "Priya Sharma",
        "manager_key": "priya",
        "mentor": "Farah Khan",
        "experience": "5 years",
        "education": "B.Des Interaction Design",
        "skills": ["Figma", "UX Research", "Prototyping"],
        "join_offset": 2,
        "status": "ONBOARDING",
    },
]

TASK_TEMPLATES = [
    ("Complete HR documentation", "Sign offer letter, submit ID proofs and bank details.", "HR", "HIGH", 1),
    ("Complete security training", "Finish the mandatory information security module.", "Compliance", "HIGH", 2),
    ("Setup laptop", "Collect device from IT and complete initial configuration.", "IT", "HIGH", 1),
    ("Setup Git and code access", "Create Git account, add SSH keys, request repository access.", "IT", "MEDIUM", 3),
    ("Setup development environment", "Install required tooling and clone primary repositories.", "Engineering", "MEDIUM", 4),
    ("Meet manager", "Introductory 1:1 with the reporting manager.", "People", "HIGH", 2),
    ("Meet team", "Team introduction session.", "People", "MEDIUM", 3),
    ("Meet mentor", "Kickoff meeting with the assigned onboarding buddy.", "People", "MEDIUM", 3),
    ("Read engineering handbook", "Go through coding standards, review process and on-call policy.", "Engineering", "LOW", 5),
    ("Complete first technical task", "Pick up a starter ticket and ship it through code review.", "Engineering", "MEDIUM", 10),
]

MEETING_TEMPLATES = [
    ("HR Orientation", 1, "10:00", "11:00"),
    ("Manager 1:1", 1, "14:00", "14:30"),
    ("Team Introduction", 2, "11:00", "12:00"),
    ("Mentor Meeting", 3, "15:00", "15:30"),
    ("Security Training", 2, "16:00", "17:00"),
    ("Project Introduction", 4, "10:30", "11:30"),
]


def _next_workday(d: date) -> date:
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def seed_if_empty(db: Session) -> bool:
    if db.scalar(select(func.count()).select_from(Employee)):
        return False

    created: dict[str, tuple[Employee, date]] = {}
    today = date.today()

    # Pass 1: managers first so pass 2 can attach manager_id.
    ordered = sorted(SEED_EMPLOYEES, key=lambda s: s["manager_key"] is not None)
    for spec in ordered:
        joining = _next_workday(today + timedelta(days=spec["join_offset"]))
        manager_id = created[spec["manager_key"]][0].id if spec["manager_key"] else None
        emp = crud.create_employee(
            db,
            {
                **{k: v for k, v in spec.items() if k not in ("join_offset", "key", "manager_key", "status")},
                "manager_id": manager_id,
                "joining_date": joining,
                "status": spec["status"],
            },
        )
        created[spec["key"]] = (emp, joining)
        crud.default_leave_balances(db, emp.id)

    # Tasks: ACTIVE employees have long since finished; onboarding folks are partial.
    for spec in SEED_EMPLOYEES:
        emp, joining = created[spec["key"]]
        if spec["status"] == "ACTIVE":
            completion_ratio = 1.0
        else:
            days_since = (today - joining).days
            completion_ratio = min(0.85, max(0.0, days_since / 14))
        for t_idx, (title, desc, cat, prio, day_off) in enumerate(TASK_TEMPLATES):
            status = (
                TaskStatus.COMPLETED
                if (t_idx + 1) / len(TASK_TEMPLATES) <= completion_ratio
                else TaskStatus.TODO
            )
            crud.create_task(
                db,
                emp.id,
                title=title,
                description=desc,
                category=cat,
                priority=prio,
                status=status,
                due_date=_next_workday(joining + timedelta(days=day_off)),
            )

    # Meetings: focus them on the onboarding employees.
    meetings_created = 0
    for key in ("arun", "sneha", "daniel"):
        emp, joining = created[key]
        for title, day_off, start, end in MEETING_TEMPLATES:
            if meetings_created >= 9:
                break
            m_date = _next_workday(joining + timedelta(days=day_off))
            if m_date < today:
                m_date = _next_workday(today + timedelta(days=(m_date - today).days % 5 + 1))
            crud.create_meeting(
                db,
                emp.id,
                title=title,
                date=m_date,
                start_time=start,
                end_time=end,
                participants=[emp.name, emp.manager or "HR"],
                status=MeetingStatus.SCHEDULED,
            )
            meetings_created += 1

    # Leave requests: one pending for Arun (manager must decide), one for Vikram,
    # one already-decided for Sneha.
    arun = created["arun"][0]
    vikram = created["vikram"][0]
    sneha = created["sneha"][0]
    crud.create_leave_request(
        db, arun.id, leave_type=LeaveType.CASUAL,
        start_date=today + timedelta(days=3), end_date=today + timedelta(days=5),
        days=3, reason="Personal work", status=LeaveStatus.PENDING, requires_approval=True,
        agent_notes="Exceeds 2-day casual leave auto-approval limit; routed to manager approval.",
    )
    crud.create_leave_request(
        db, vikram.id, leave_type=LeaveType.EARNED,
        start_date=today + timedelta(days=8), end_date=today + timedelta(days=12),
        days=5, reason="Family function", status=LeaveStatus.PENDING, requires_approval=True,
    )
    lr3 = crud.create_leave_request(
        db, sneha.id, leave_type=LeaveType.SICK,
        start_date=today - timedelta(days=4), end_date=today - timedelta(days=4),
        days=1, reason="Fever", status=LeaveStatus.APPROVED, requires_approval=False,
        agent_notes="Single-day sick leave; auto-approved per leave policy.",
    )
    crud.decide_leave_request(db, lr3.id, approve=True)

    crud.log_agent(db, "System", "seed_data",
                   detail="Seeded demo employees, tasks, meetings and leave requests.")
    return True


# Roles come from the email prefix (app.security.role_from_email) — the same
# policy used when HR adds a user. A *recognised* role prefix always wins; when
# the prefix is not a role keyword (e.g. 'anil.menon', whose address carries no
# employee id at all), the org hierarchy decides: anyone with direct reports is
# a MANAGER, everyone else a plain EMPLOYEE.
DEFAULT_ROLE = Role.EMPLOYEE


def _seeded_role(db, emp) -> Role:
    """Resolve a seeded employee's role: recognised email prefix, then hierarchy."""
    from app.security import EMAIL_ROLE_PREFIXES, email_role_prefix, role_from_email

    prefix = email_role_prefix(emp.email)
    if prefix in EMAIL_ROLE_PREFIXES:
        return role_from_email(emp.email)
    return Role.MANAGER if crud.team_employee_ids(db, emp.id) else DEFAULT_ROLE


def seed_users(db: Session) -> bool:
    """Create a login for every seeded employee. Idempotent."""
    if crud.count_users(db):
        return False
    from app.config import settings

    created_any = False
    for spec in SEED_EMPLOYEES:
        emp = crud.get_employee_by_email(db, spec["email"])
        if not emp:
            continue
        crud.create_user(
            db,
            email=spec["email"],
            name=spec["name"],
            hashed_password=hash_password(settings.demo_password),
            role=_seeded_role(db, emp),
            employee_id=emp.id,
        )
        created_any = True

    crud.log_agent(
        db, "System", "seed_users",
        detail=f"Seeded {created_any} login accounts (password: demo default).",
    )
    return created_any
