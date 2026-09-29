"""SQLAlchemy ORM models for the onboarding system."""
import enum
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskStatus(str, enum.Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    OVERDUE = "OVERDUE"


class MeetingStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class LeaveStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class LeaveType(str, enum.Enum):
    CASUAL = "CASUAL"
    SICK = "SICK"
    EARNED = "EARNED"


class Role(str, enum.Enum):
    """Access-control role. Distinct from Employee.role, which is a job title."""

    HR = "HR"
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"


class User(Base):
    """Login account. HR users have no employee_id; the other roles always do."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        Enum(Role, values_callable=lambda e: [m.value for m in e]), default=Role.EMPLOYEE
    )
    employee_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"), index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    employee: Mapped["Employee | None"] = relationship()


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # e.g. EMP001
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    role: Mapped[str | None] = mapped_column(String(120))
    department: Mapped[str | None] = mapped_column(String(120))
    manager: Mapped[str | None] = mapped_column(String(120))
    manager_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"), index=True)
    mentor: Mapped[str | None] = mapped_column(String(120))
    experience: Mapped[str | None] = mapped_column(String(64))
    education: Mapped[str | None] = mapped_column(Text)
    skills: Mapped[list | None] = mapped_column(JSON)
    joining_date: Mapped[date] = mapped_column(Date, default=date.today)
    status: Mapped[str] = mapped_column(String(32), default="ONBOARDING")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    tasks: Mapped[list["OnboardingTask"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    meetings: Mapped[list["Meeting"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    leave_requests: Mapped[list["LeaveRequest"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    balances: Mapped[list["LeaveBalance"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"))
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str | None] = mapped_column(String(512))
    extracted_text: Mapped[str | None] = mapped_column(Text)
    extracted_data: Mapped[dict | None] = mapped_column(JSON)
    extraction_method: Mapped[str] = mapped_column(String(32), default="llm")  # llm | fallback
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, values_callable=lambda e: [m.value for m in e]),
        default=TaskStatus.TODO,
    )
    priority: Mapped[str] = mapped_column(String(16), default="MEDIUM")  # LOW/MEDIUM/HIGH
    due_date: Mapped[date | None] = mapped_column(Date)
    category: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    employee: Mapped["Employee"] = relationship(back_populates="tasks")


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM 24h
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)
    participants: Mapped[list | None] = mapped_column(JSON)
    status: Mapped[MeetingStatus] = mapped_column(
        Enum(MeetingStatus, values_callable=lambda e: [m.value for m in e]),
        default=MeetingStatus.SCHEDULED,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    employee: Mapped["Employee"] = relationship(back_populates="meetings")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), index=True)
    leave_type: Mapped[LeaveType] = mapped_column(
        Enum(LeaveType, values_callable=lambda e: [m.value for m in e]), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    days: Mapped[int] = mapped_column(Integer, default=1)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[LeaveStatus] = mapped_column(
        Enum(LeaveStatus, values_callable=lambda e: [m.value for m in e]),
        default=LeaveStatus.PENDING,
    )
    requires_approval: Mapped[bool] = mapped_column(default=True)
    policy_context: Mapped[list | None] = mapped_column(JSON)
    agent_notes: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[str | None] = mapped_column(String(128))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime)
    thread_id: Mapped[str | None] = mapped_column(String(64))  # LangGraph checkpoint thread
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    employee: Mapped["Employee"] = relationship(back_populates="leave_requests")


class LeaveBalance(Base):
    __tablename__ = "leave_balances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), index=True)
    leave_type: Mapped[LeaveType] = mapped_column(
        Enum(LeaveType, values_callable=lambda e: [m.value for m in e]), nullable=False
    )
    total_days: Mapped[int] = mapped_column(Integer, default=0)
    used_days: Mapped[int] = mapped_column(Integer, default=0)
    year: Mapped[int] = mapped_column(Integer, default=datetime.now().year)

    employee: Mapped["Employee"] = relationship(back_populates="balances")

    @property
    def remaining_days(self) -> int:
        return max(0, self.total_days - self.used_days)


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    employee_id: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="completed")  # completed|warning|error
    detail: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
