from datetime import datetime
from decimal import Decimal
from typing import Any

from ninja import Schema
from pydantic import Field


class ScoringCriterionOut(Schema):
    id: int
    name: str
    description: str
    weight: Decimal
    max_score: Decimal
    score_type: str
    is_required: bool
    is_active: bool
    order: int


class ScoringCriterionIn(Schema):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    weight: Decimal = Field(default=Decimal("1"), ge=0)
    max_score: Decimal = Field(..., gt=0)
    score_type: str = Field(default="numeric")
    is_required: bool = True
    is_active: bool = True
    order: int = Field(default=0, ge=0)


class ApplicationScoreIn(Schema):
    criterion_id: int
    score: Decimal
    comment: str = ""


class ApplicationScoreOut(Schema):
    id: int
    criterion_id: int
    criterion_name: str
    score: Decimal
    comment: str
    updated_at: datetime


class ScorerOut(Schema):
    id: str
    username: str


class ApplicationScoringOut(Schema):
    id: int
    application_id: str
    scorer: ScorerOut
    status: str
    submitted_at: datetime | None
    scores: list[ApplicationScoreOut]
    created_at: datetime
    updated_at: datetime


class ApplicationScoringUpsert(Schema):
    scores: list[ApplicationScoreIn]


class ApplicationScoringPatch(Schema):
    status: str | None = None
    scores: list[ApplicationScoreIn] | None = None


class ScorerTotalOut(Schema):
    scorer_id: str
    username: str
    status: str
    total_raw: Decimal
    total_weighted: Decimal


class CriterionMeanOut(Schema):
    criterion_id: int
    name: str
    mean_score: Decimal | None
    weight: Decimal


class ApplicationScoringSummary(Schema):
    application_id: str
    scorers: list[ScorerTotalOut]
    criteria: list[CriterionMeanOut]
    overall_weighted_mean: Decimal | None
