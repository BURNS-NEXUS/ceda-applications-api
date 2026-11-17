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


class ApplicationListOut(Schema):
    total: int
    data: list[ApplicationOut]
