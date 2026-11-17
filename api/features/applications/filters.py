from datetime import date
from decimal import Decimal

from django.db.models import Q, QuerySet
from ninja import Schema
from pydantic import Field

from .models import Application


class ApplicationFilters(Schema):
    skip: int = Field(default=0, ge=0)
    take: int | None = Field(default=None, ge=0)
    search: str | None = None
    status_in: list[str] | None = None
    status_not_in: list[str] | None = None

    created_at_eq: date | None = None
    created_at_gt: date | None = None
    created_at_gte: date | None = None
    created_at_lt: date | None = None
    created_at_lte: date | None = None
    updated_at_eq: date | None = None
    updated_at_gt: date | None = None
    updated_at_gte: date | None = None
    updated_at_lt: date | None = None
    updated_at_lte: date | None = None
    incorporation_date_eq: date | None = None
    incorporation_date_gt: date | None = None
    incorporation_date_gte: date | None = None
    incorporation_date_lt: date | None = None
    incorporation_date_lte: date | None = None
    loan_amount_eq: Decimal | None = None
    loan_amount_gt: Decimal | None = None
    loan_amount_gte: Decimal | None = None
    loan_amount_lt: Decimal | None = None
    loan_amount_lte: Decimal | None = None

    def apply(self, applications: QuerySet[Application]) -> QuerySet[Application]:
        if self.search is not None:
            applications = applications.filter(
                Q(project_title__icontains=self.search)
                | Q(company_no__icontains=self.search)
                | Q(email__icontains=self.search)
            )
        if self.status_in is not None:
            applications = applications.filter(state__in=self.status_in)
        if self.status_not_in is not None:
            applications = applications.exclude(state__in=self.status_not_in)

        for field in ("created_at", "updated_at", "incorporation_date", "loan_amount"):
            lookup_field = (
                f"{field}__date" if field in ("created_at", "updated_at") else field
            )
            for operator in ("eq", "gt", "gte", "lt", "lte"):
                value = getattr(self, f"{field}_{operator}")
                if value is not None:
                    lookup = "exact" if operator == "eq" else operator
                    applications = applications.filter(
                        **{f"{lookup_field}__{lookup}": value}
                    )
        return applications
