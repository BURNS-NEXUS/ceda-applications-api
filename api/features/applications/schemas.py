from datetime import date

from ninja import Schema


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


class ApplicationListOut(Schema):
    total: int
    data: list[ApplicationOut]


class FeebackAplicationIn(Schema):
    reason: str
