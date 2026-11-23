from datetime import datetime
from typing import Any

from ninja import Schema
from pydantic import Field


class AuditLogFilters(Schema):
    skip: int = Field(default=0, ge=0)
    take: int | None = Field(default=None, ge=0)


class AuditLogOut(Schema):
    id: str
    actor_id: str | None
    actor_username: str | None = None
    action: str
    resource_type: str
    resource_id: str
    details: Any
    created_at: datetime


class AuditLogListOut(Schema):
    total: int
    data: list[AuditLogOut]
