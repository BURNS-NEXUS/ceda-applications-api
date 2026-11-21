from decimal import Decimal

from ninja import Schema
from pydantic import Field


class SettingsOut(Schema):
    site_name: str = Field(
        ...,
        description="Public name of the application.",
        examples=["CEDA Applications"],
    )
    maintenance_mode: bool = Field(
        ...,
        description=(
            "When true, clients should display a maintenance notice and avoid "
            "starting new application workflows."
        ),
        examples=[False],
    )
    evaluators_per_application: int = Field(
        ...,
        ge=1,
        description=(
            "Number of evaluators that must be assigned to each application."
        ),
        examples=[2],
    )
    minimum_score: Decimal = Field(
        ...,
        ge=0,
        description="Minimum adjudication score required for acceptance.",
        examples=[0],
    )


class SettingsIn(Schema):
    site_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Public name of the application.",
        examples=["CEDA Applications"],
    )
    maintenance_mode: bool | None = Field(
        default=None,
        description="Enable or disable maintenance mode.",
        examples=[True],
    )
    evaluators_per_application: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Number of evaluators that must be assigned to each application. "
            "Must be at least 1."
        ),
        examples=[3],
    )
    minimum_score: Decimal | None = Field(
        default=None,
        ge=0,
        description="Minimum adjudication score required for acceptance.",
        examples=[50],
    )
