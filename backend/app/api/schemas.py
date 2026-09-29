"""Pydantic request/response models for the API."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ------------------------------- Auth ------------------------------------- #

class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str
    role: str
    employee_id: Optional[str] = None


class LoginRoleUpdate(BaseModel):
    role: Literal["HR", "MANAGER", "EMPLOYEE"]


class RolePreview(BaseModel):
    """What role an email address would be granted, before the user is created."""
    email: str
    prefix: str
    role: str
    recognized: bool
    reason: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class SignupRequest(BaseModel):
    """Public self-registration.

    There is deliberately no `role` or `login_role` field. A self-registered
    account is always EMPLOYEE; MANAGER and HR access is granted afterwards by
    an existing privileged user. Accepting a role here would let anyone register
    as HR just by choosing an email address.
    """

    name: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=r"^[\w.+-]+@[\w-]+\.[\w.]+$", max_length=160)
    password: str = Field(min_length=8, max_length=128)


# ----------------------------- Employees ---------------------------------- #

class EmployeeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=r"^[\w.+-]+@[\w-]+\.[\w.]+$")
    phone: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    manager: Optional[str] = None
    mentor: Optional[str] = None
    experience: Optional[str] = None
    education: Optional[str] = None
    skills: Optional[list[str]] = None
    joining_date: Optional[date] = None

    # --- login provisioning ---
    # The access role is normally derived from the email prefix; these let HR
    # override that, or set a specific initial password.
    login_role: Optional[Literal["HR", "MANAGER", "EMPLOYEE"]] = None
    login_name: Optional[str] = Field(default=None, max_length=120)
    login_password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    email: str
    phone: Optional[str]
    role: Optional[str]
    department: Optional[str]
    manager: Optional[str]
    mentor: Optional[str]
    experience: Optional[str]
    education: Optional[str]
    skills: Optional[list[str]]
    joining_date: date
    status: str
    created_at: datetime


class EmployeeCreated(EmployeeOut):
    """Employee plus the login that was provisioned for them."""
    login_email: str
    login_role: str
    role_source: str          # "email_prefix" | "explicit"
    role_reason: str          # human-readable explanation of the derived role
    default_password: bool    # True => password is the shared demo password


class EmployeeDetail(EmployeeOut):
    progress: dict = {}
    tasks: list["TaskOut"] = []
    meetings: list["MeetingOut"] = []
    leave_requests: list["LeaveOut"] = []
    balances: list["BalanceOut"] = []


# ----------------------------- Resumes ------------------------------------ #

class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: Optional[str]
    filename: str
    extracted_data: Optional[dict]
    extraction_method: str
    created_at: datetime


# ------------------------------ Tasks ------------------------------------- #

class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: str
    title: str
    description: Optional[str]
    status: str
    priority: str
    due_date: Optional[date]
    category: Optional[str]
    created_at: datetime
    employee_name: Optional[str] = None


class TaskUpdate(BaseModel):
    status: Literal["TODO", "IN_PROGRESS", "COMPLETED", "OVERDUE"]


# ----------------------------- Meetings ----------------------------------- #

class MeetingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: str
    title: str
    date: date
    start_time: str
    end_time: str
    participants: Optional[list[str]]
    status: str
    employee_name: Optional[str] = None


class MeetingCreate(BaseModel):
    employee_id: str
    title: str = Field(min_length=2)
    date: date
    start_time: Optional[str] = None   # HH:MM; if omitted, agent finds a slot
    end_time: Optional[str] = None
    participants: Optional[list[str]] = None


class MeetingUpdate(BaseModel):
    date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[Literal["SCHEDULED", "COMPLETED", "CANCELLED"]] = None


# ------------------------------ Leave ------------------------------------- #

class LeaveCreate(BaseModel):
    employee_id: str
    leave_type: Literal["CASUAL", "SICK", "EARNED"]
    start_date: date
    end_date: date
    reason: Optional[str] = None


class MyLeaveCreate(BaseModel):
    """Self-service variant — employee_id comes from the token, not the body."""

    leave_type: Literal["CASUAL", "SICK", "EARNED"]
    start_date: date
    end_date: date
    reason: Optional[str] = None


class LeaveOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: str
    leave_type: str
    start_date: date
    end_date: date
    days: int
    reason: Optional[str]
    status: str
    requires_approval: bool
    agent_notes: Optional[str]
    decided_by: Optional[str]
    thread_id: Optional[str]
    created_at: datetime
    employee_name: Optional[str] = None


class BalanceOut(BaseModel):
    id: int
    employee_id: str
    leave_type: str
    total_days: int
    used_days: int
    remaining_days: int


# ------------------------------ Policy ------------------------------------ #

class PolicyQuery(BaseModel):
    question: str = Field(min_length=3)


class PolicySource(BaseModel):
    source: str
    content: str
    score: Optional[float] = None


class PolicyAnswer(BaseModel):
    question: str
    answer: str
    sources: list[PolicySource]


# ------------------------------- Agent ------------------------------------ #

class AgentRunRequest(BaseModel):
    message: Optional[str] = None
    request_type: Optional[Literal["resume", "leave", "meeting", "policy", "onboarding"]] = None
    employee_id: Optional[str] = None
    leave_request: Optional[dict] = None
    meeting_request: Optional[dict] = None


class AgentLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    agent: str
    action: str
    employee_id: Optional[str]
    status: str
    detail: Optional[str]
    timestamp: datetime


class MessageOut(BaseModel):
    role: str
    agent: Optional[str] = None
    content: str


class AgentRunResponse(BaseModel):
    thread_id: str
    messages: list[MessageOut] = []
    error: Optional[str] = None
    requires_human_approval: bool = False
    leave_status: Optional[str] = None
    policy_answer: Optional[str] = None
    policy_context: list[dict] = []
    employee_data: Optional[dict] = None
    resume_data: Optional[dict] = None
    meetings: list[dict] = []
    result: dict[str, Any] = {}


EmployeeDetail.model_rebuild()
