from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ninja import Schema
from pydantic import Field


class ReportFilters(Schema):
    date_from: date | None = None
    date_to: date | None = None
    status_in: list[str] | None = None
    status_not_in: list[str] | None = None
    search: str | None = None


class PipelineStateCount(Schema):
    state: str
    count: int


class PipelineReport(Schema):
    total: int
    by_state: dict[str, int]
    funnel: list[PipelineStateCount]


class StatusBreakdownRow(Schema):
    status: str
    count: int


class ProcessingTimeReport(Schema):
    terminal_count: int
    average_cycle_days: float
    by_state: list[dict[str, Any]]


class ReviewerWorkloadRow(Schema):
    employee_id: str
    username: str
    assigned: int
    completed_tasks: int


class ScoringSummaryReport(Schema):
    applications: int
    accepted: int
    rejected: int
    pending_review: int
    adjudication_count: int
    average_final_score: float | None = None


class DashboardKPIs(Schema):
    total_applications: int
    submitted_applications: int
    accepted: int
    rejected: int
    conversion_rate_percent: float
    stalled_applications: int
    overdue_tasks: int


class ReportTemplateIn(Schema):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    filters: dict[str, Any] = Field(default_factory=dict)


class ReportTemplateOut(Schema):
    id: str
    name: str
    description: str
    filters: dict[str, Any]
    created_at: datetime
    updated_at: datetime