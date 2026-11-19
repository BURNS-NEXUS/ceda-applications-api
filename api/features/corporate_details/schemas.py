from datetime import date, datetime
from decimal import Decimal

from ninja import Schema
from pydantic import Field


class CorporateResourceFilters(Schema):
    """Optional filters shared by corporate-detail list endpoints."""

    application_id: str | None = Field(
        default=None,
        description="Restrict results to records belonging to this application.",
    )


class DeleteResult(Schema):
    """Result returned after deleting a corporate-detail record."""

    success: bool = Field(description="True when the record was deleted.")


class CorporateDetailsIn(Schema):
    application_id: str = Field(
        description="Application this corporate-details record belongs to."
    )
    name_of_company: str = Field(description="Registered company name.")
    date_of_incorporation: date = Field(description="Company incorporation date.")
    nature_of_company: str = Field(
        description="Nature or primary business activity of the company."
    )


class CorporateDetailsPatch(Schema):
    application_id: str = Field(
        description="Application containing the corporate-details record."
    )
    name_of_company: str | None = Field(
        default=None, description="Replacement registered company name."
    )
    date_of_incorporation: date | None = Field(
        default=None, description="Replacement incorporation date."
    )
    nature_of_company: str | None = Field(
        default=None, description="Replacement nature of company."
    )


class CorporateDetailsOut(CorporateDetailsIn):
    id: str = Field(description="Unique corporate-details record identifier.")
    created_at: datetime = Field(description="Record creation timestamp.")
    updated_at: datetime = Field(description="Record last-update timestamp.")


class CorporateDetailsListOut(Schema):
    total: int = Field(description="Total number of matching corporate-detail records.")
    data: list[CorporateDetailsOut] = Field(description="Corporate-detail records.")


class ShareholderIn(Schema):
    application_id: str = Field(
        description="Application this shareholder record belongs to."
    )
    company_id: str = Field(
        description="Corporate-details record representing the shareholder's company."
    )
    name: str = Field(description="Shareholder full name.")
    dob: date = Field(description="Shareholder date of birth.")
    nationality: str = Field(description="Shareholder nationality.")
    id_number: str = Field(
        description="Shareholder national identity or passport number."
    )
    position: str = Field(description="Shareholder position within the company.")
    total_authorized_share_capital: Decimal = Field(
        description="Total authorized share capital.",
        ge=0,
        max_digits=15,
        decimal_places=2,
    )
    total_issued_share_capital: Decimal = Field(
        description="Total issued share capital.",
        ge=0,
        max_digits=15,
        decimal_places=2,
    )


class ShareholderPatch(Schema):
    application_id: str = Field(
        description="Application containing the shareholder record."
    )
    company_id: str | None = Field(
        default=None, description="Replacement corporate-details record identifier."
    )
    name: str | None = Field(default=None, description="Replacement shareholder name.")
    dob: date | None = Field(
        default=None, description="Replacement shareholder date of birth."
    )
    nationality: str | None = Field(
        default=None, description="Replacement shareholder nationality."
    )
    id_number: str | None = Field(
        default=None, description="Replacement identity or passport number."
    )
    position: str | None = Field(
        default=None, description="Replacement shareholder position."
    )
    total_authorized_share_capital: Decimal | None = Field(
        default=None,
        description="Replacement total authorized share capital.",
        ge=0,
        max_digits=15,
        decimal_places=2,
    )
    total_issued_share_capital: Decimal | None = Field(
        default=None,
        description="Replacement total issued share capital.",
        ge=0,
        max_digits=15,
        decimal_places=2,
    )


class ShareholderOut(ShareholderIn):
    id: str = Field(description="Unique shareholder record identifier.")
    created_at: datetime = Field(description="Record creation timestamp.")
    updated_at: datetime = Field(description="Record last-update timestamp.")


class ShareholderListOut(Schema):
    total: int = Field(description="Total number of matching shareholder records.")
    data: list[ShareholderOut] = Field(description="Shareholder records.")
