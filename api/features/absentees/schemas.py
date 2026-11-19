from datetime import date, datetime
from typing import Literal

from ninja import Schema
from pydantic import Field


class AbsenteeOut(Schema):
    id: str
    user_id: str
    username: str
    leave_type: str
    start_date: date
    end_date: date | None
    reason: str
    is_on_leave: bool
    created_at: datetime
    updated_at: datetime


class AbsenteeCreateIn(Schema):
    """Payload for adding (or updating) an employee's absence."""

    user_id: str = Field(
        ...,
        description="ID (primary key) of the user who is absent.",
        examples=["cm8xyzabcdef1234567890abcd"],
    )
    leave_type: Literal[
        "vacation",
        "sick",
        "personal",
        "unpaid",
        "other",
    ] = Field(
        ...,
        description="Kind of leave the user is taking.",
        examples=["sick"],
    )
    start_date: date = Field(
        ...,
        description="First day of the leave.",
        examples=["2026-12-01"],
    )
    end_date: date | None = Field(
        default=None,
        description="Last day of the leave. Omit for open-ended leave.",
        examples=["2026-12-14"],
    )
    reason: str = Field(
        default="",
        description="Optional reason for the absence.",
        examples=["Medical appointment"],
    )


class DeleteResult(Schema):
    success: bool
