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


class ScoringCriterionPatch(Schema):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    weight: Decimal | None = Field(default=None, ge=0)
    max_score: Decimal | None = Field(default=None, gt=0)
    score_type: str | None = None
    is_required: bool | None = None
    is_active: bool | None = None
    order: int | None = Field(default=None, ge=0)


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
    overall_comment: str
    evidence_reference: str
    no_conflict_declared: bool
    id: int
    application_id: str
    scorer: ScorerOut
    status: str
    submitted_at: datetime | None
    confirmed_at: datetime | None = None
    scores: list[ApplicationScoreOut]
    created_at: datetime
    updated_at: datetime


class ApplicationScoringUpsert(Schema):
    overall_comment: str | None = None
    evidence_reference: str | None = None
    no_conflict_declared: bool | None = None
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


class ApplicationAdjudicationOut(Schema):
    id: int
    application_id: str
    adjudicator: ScorerOut
    final_score: Decimal | None = None
    comment: str = ""
    status: str
    scores: list[ApplicationScoreOut]
    confirmed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ApplicationAdjudicationIn(Schema):
    scores: list[ApplicationScoreIn]
    comment: str | None = None
