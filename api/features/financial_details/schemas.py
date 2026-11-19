from datetime import datetime
from decimal import Decimal

from ninja import Schema
from pydantic import Field


class FinancialDetailsFilters(Schema):
    """Optional filters shared by financial details list endpoints."""

    application_id: str | None = Field(
        default=None,
        description="Restrict results to records belonging to this application.",
    )


class DeleteResult(Schema):
    """Result returned after deleting a financial-detail record."""

    success: bool = Field(description="True when the record was deleted.")


class LoanIn(Schema):
    application_id: str = Field(description="Application this loan belongs to.")
    institution_name: str = Field(description="Name of the lending institution.")
    account_number: str = Field(description="Loan or financing account number.")
    loan_amount: Decimal = Field(
        description="Original or approved loan amount.",
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    repayment_amount: Decimal = Field(
        description="Amount repaid per repayment period.",
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    repayment_period: int = Field(
        description="Total repayment period in months.",
        ge=1,
    )
    amount_outstanding: Decimal = Field(
        description="Amount still outstanding on the loan.",
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    is_past_loan: bool = Field(
        description="Whether this is a historical loan rather than a current loan."
    )


class LoanPatch(Schema):
    application_id: str = Field(description="Application containing the loan record.")
    institution_name: str | None = Field(
        default=None, description="Replacement lending institution name."
    )
    account_number: str | None = Field(
        default=None, description="Replacement loan account number."
    )
    loan_amount: Decimal | None = Field(
        default=None,
        description="Replacement loan amount.",
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    repayment_amount: Decimal | None = Field(
        default=None,
        description="Replacement repayment amount.",
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    repayment_period: int | None = Field(
        default=None,
        description="Replacement repayment period in months.",
        ge=1,
    )
    amount_outstanding: Decimal | None = Field(
        default=None,
        description="Replacement outstanding amount.",
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    is_past_loan: bool | None = Field(
        default=None, description="Replacement past-loan indicator."
    )


class LoanOut(LoanIn):
    id: str = Field(description="Unique loan record identifier.")
    created_at: datetime = Field(description="Record creation timestamp.")
    updated_at: datetime = Field(description="Record last-update timestamp.")


class LoanListOut(Schema):
    total: int = Field(description="Total number of matching loan records.")
    data: list[LoanOut] = Field(description="Loan records.")
