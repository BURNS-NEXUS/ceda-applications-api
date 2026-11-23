from datetime import datetime

from ninja import Schema
from pydantic import Field


class TaskAssigneeOut(Schema):
    id: str
    username: str
    email: str


class TaskOut(Schema):
    id: str
    application_id: str
    task_type: str
    status: str
    assignees: list[TaskAssigneeOut]
    created_at: datetime
    updated_at: datetime


class TaskListOut(Schema):
    total: int
    data: list[TaskOut]


class TaskAssignIn(Schema):
    user_id: str


class ConflictDeclarationIn(Schema):
    declaration: str = Field(min_length=10)
    reason: str = Field(min_length=10)


class ConflictDeclarationOut(Schema):
    id: str
    task_id: str
    employee_id: str
    declaration: str
    reason: str
    created_at: datetime


class SupervisorOut(Schema):
    user_id: str
    username: str
    email: str


class SupervisorIn(Schema):
    user_id: str


class TaskPoolItemOut(Schema):
    id: str
    application_id: str
    project_title: str
    company_no: str
    business_nature: str
    sector: str
    sector_label: str
    expertise_match: bool
    required_assignees: int
    assigned_count: int
    created_at: datetime


class TaskPoolOut(Schema):
    total: int
    data: list[TaskPoolItemOut]


class ClaimTaskIn(Schema):
    reason: str = ""


class DeclineTaskIn(Schema):
    reason: str = Field(min_length=10)


class ExpertiseIn(Schema):
    sectors: list[str]


class ExpertiseOut(Schema):
    user_id: str
    username: str
    sectors: list[str]
