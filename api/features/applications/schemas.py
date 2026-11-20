from datetime import date, datetime
from typing import Literal

from ninja import Schema

from api.features.corporate_details.schemas import (
    CorporateDetailsOut,
    ShareholderOut,
)
from api.features.financial_details.schemas import LoanOut
from api.features.personal_details.schemas import (
    AddressOut,
    ContactOut,
    EmploymentOut,
    PersonalDetailsOut,
)
from api.features.references.schemas import (
    CommercialBankerOut,
    NextOfKinOut,
    ReferenceOut,
)


class ApplicationOut(Schema):
    id: str
    project_title: str
    state: str
    company_no: str
    incorporation_date: date
    contact_person: str
    telephone: str
    business_nature: str
    business_location: str
    loan_amount: float
    email: str
    has_current_loan_with_other: bool
    has_past_loan_with_other: bool
    application_type: Literal["individual", "company", "all"]


class ApplicationIn(Schema):
    project_title: str
    company_no: str
    incorporation_date: date
    contact_person: str
    telephone: str
    business_nature: str
    business_location: str
    loan_amount: float
    email: str
    has_current_loan_with_other: bool
    has_past_loan_with_other: bool
    application_type: Literal["individual", "company", "all"]


class ApplicationPatch(Schema):
    project_title: str | None = None
    company_no: str | None = None
    incorporation_date: date | None = None
    contact_person: str | None = None
    telephone: str | None = None
    business_nature: str | None = None
    business_location: str | None = None
    loan_amount: float | None = None
    email: str | None = None
    has_current_loan_with_other: bool | None = None
    has_past_loan_with_other: bool | None = None
    application_type: Literal["individual", "company", "all"] | None = None


class ApplicationListOut(Schema):
    total: int
    data: list[ApplicationOut]


class EvaluationScoreDetailOut(Schema):
    id: str
    criterion_id: str
    score: int
    comments: str


class EvaluationDetailOut(Schema):
    id: str
    evaluator_id: str
    comments: str
    created_at: datetime
    updated_at: datetime
    scores: list[EvaluationScoreDetailOut]


class ClarificationDetailOut(Schema):
    id: str
    version: int
    reason: str
    response: str | None
    created_by_id: str | None
    created_at: datetime


class ApplicationDetailOut(ApplicationOut):
    personal_details: list[PersonalDetailsOut]
    addresses: list[AddressOut]
    contacts: list[ContactOut]
    employments: list[EmploymentOut]
    corporate_details: list[CorporateDetailsOut]
    shareholders: list[ShareholderOut]
    loans: list[LoanOut]
    references: list[ReferenceOut]
    commercial_bankers: list[CommercialBankerOut]
    next_of_kin: list[NextOfKinOut]
    evaluations: list[EvaluationDetailOut]
    clarifications: list[ClarificationDetailOut]


class FeedbackApplicationIn(Schema):
    reason: str
