from datetime import datetime
from typing import Any

from ninja import Schema
from pydantic import Field


class ClarificationFilters(Schema):
    skip: int = Field(default=0, ge=0)
    take: int | None = Field(default=None, ge=0)
    application_id: str | None = None
    version: int | None = Field(default=None, ge=0)


class ClarificationOut(Schema):
    id: str
    created_by: str | None
    application_id: str
    version: int
    reason: str
    response: str | None
    created_at: datetime

    @staticmethod
    def resolve_created_by(obj):
        return str(obj.created_by_id) if obj.created_by_id is not None else None


class ClarificationListOut(Schema):
    total: int
    data: list[ClarificationOut]
