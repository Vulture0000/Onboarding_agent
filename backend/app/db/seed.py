"""Seed realistic demo data on first startup (only if DB is empty)."""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import crud
from app.db.models import (
    Employee,
    LeaveRequest,
    LeaveStatus,
    LeaveType,
    MeetingStatus,
    TaskStatus,
)

SEED_EMPLOYEES = [
    {
        "name": "Arun Kumar",
        "email": "arun.kumar@example.com",
        "phone": "+91 98765 43210",
        "role": "Software Engineer",
        "department": "Engineering",
        "manager": "Priya Sharma",
        "mentor": "Rahul Verma",
        "experience": "Fresher",
        "education": "B.E Computer Science",
        "skills": ["Python", "FastAPI", "React"],
        "join_offset": -12,
    },
    {
        "name": "Sneha Patel",
        "email": "sneha.patel@example.com",
        "phone": "+91 99887 76655",
        "role": "Data Analyst",
        "department": "Data",
        "manager": "Anil Menon",
        "mentor": "Kavya Nair",
        "experience": "2 years",
        "education": "M.Sc Statistics",
        "skills": ["SQL", "Python", "Power BI"],
        "join_offset": -8,
    },
    {
        "name": "Vikram Singh",
        "email": "vikram.singh@example.com",
        "phone": "+91 90909 80807",
        "role": "DevOps Engineer",
        "department": "Engineering",
        "manager": "Priya Sharma",
        "mentor": "Rahul Verma",
        "experience": "4 years",
        "education": "B.Tech Information Technology",
        "skills": ["Docker", "Kubernetes", "AWS", "Terraform"],
        "join_offset": -5,
    },
    {
        "name": "Meera Iyer",
        "email": "meera.iyer@example.com",
        "phone": "+91 91234 56789",
        "role": "HR Executive",
        "department": "Human Resources",
        "manager": "Sunita Rao",
        "mentor": "Sunita Rao",
        "experience": "3 years",
        "education": "MBA Human Resources",
        "skills": ["Recruitment", "Payroll", "Employee Relations"],
        "join_offset": -3,
    },
    {
        "name": "Daniel Fernandes",
        "email": "daniel.fernandes@example.com",
        "phone": "+91 98123 45670",
        "role": "Product Designer",
        "department": "Design",
        "manager": "Nisha Gupta",
        "mentor": "Farah Khan",
        "experience": "5 years",
        "education": "B.Des Interaction Design",
        "skills": ["Figma", "UX Research", "Prototyping"],
        "join_offset": 2,
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

    created = []
    today = date.today()
    for i, spec in enumerate(SEED_EMPLOYEES):
        joining = _next_workday(today + timedelta(days=spec["join_offset"]))
        emp = crud.create_employee(
            db,
            {
                **{k: v for k, v in spec.items() if k != "join_offset"},
                "joining_date": joining,
                "status": "ONBOARDING" if spec["join_offset"] >= -10 else "ACTIVE",
            },
        )
        created.append((emp, joining))
        crud.default_leave_balances(db, emp.id)

    # Tasks: give earlier joiners partial completion so progress bars look real
    for idx, (emp, joining) in enumerate(created):
        completion_ratio = [0.8, 0.6, 0.4, 0.2, 0.0][idx]
        for t_idx, (title, desc, cat, prio, day_off) in enumerate(TASK_TEMPLATES):
            status = TaskStatus.COMPLETED if (t_idx + 1) / len(TASK_TEMPLATES) <= completion_ratio else TaskStatus.TODO
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

    # Meetings: 8 total, spread across employees
    meetings_created = 0
    for emp, joining in created:
        for title, day_off, start, end in MEETING_TEMPLATES:
            if meetings_created >= 8:
                break
            if emp.id not in ("EMP001", "EMP002", "EMP005"):
                continue
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

    # Leave requests: 3 (one pending approval, one approved, one rejected)
    emp1, emp2, _ = created[0][0], created[1][0], created[2][0]
    lr1 = crud.create_leave_request(
        db,
        emp1.id,
        leave_type=LeaveType.CASUAL,
        start_date=today + timedelta(days=3),
        end_date=today + timedelta(days=5),
        days=3,
        reason="Personal work",
        status=LeaveStatus.PENDING,
        requires_approval=True,
        agent_notes="Exceeds 2-day casual leave auto-approval limit; routed to manager approval.",
    )
    lr2 = crud.create_leave_request(
        db,
        emp2.id,
        leave_type=LeaveType.SICK,
        start_date=today - timedelta(days=4),
        end_date=today - timedelta(days=4),
        days=1,
        reason="Fever",
        status=LeaveStatus.APPROVED,
        requires_approval=False,
        agent_notes="Single-day sick leave within balance; auto-approved per leave policy.",
    )
    crud.decide_leave_request(db, lr2.id, approve=True)
    lr3 = crud.create_leave_request(
        db,
        emp1.id,
        leave_type=LeaveType.EARNED,
        start_date=today - timedelta(days=10),
        end_date=today - timedelta(days=6),
        days=5,
        reason="Family function",
        status=LeaveStatus.PENDING,
        requires_approval=True,
    )
    crud.decide_leave_request(db, lr3.id, approve=False)

    crud.log_agent(db, "System", "seed_data", detail="Seeded demo employees, tasks, meetings and leave requests.")
    return True
