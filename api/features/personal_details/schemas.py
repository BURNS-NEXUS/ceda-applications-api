from datetime import date, datetime
from decimal import Decimal

from ninja import Schema
from pydantic import Field


class ApplicantResourceFilters(Schema):
    """Optional filters shared by applicant-detail list endpoints."""

    application_id: str | None = Field(
        default=None,
        description="Restrict results to records belonging to this application.",
    )


class DeleteResult(Schema):
    """Result returned after deleting an applicant-detail record."""

    success: bool = Field(description="True when the record was deleted.")


class PersonalDetailsIn(Schema):
    application_id: str = Field(
        description="Application this personal-details record belongs to."
    )
    title: str = Field(description="Applicant title, for example Mr or Ms.")
    surname: str = Field(description="Applicant surname.")
    other_names: str = Field(description="Applicant other names.")
    id_number: str = Field(
        description="Applicant national identity or passport number."
    )
    date_of_birth: date = Field(description="Applicant date of birth.")
    marital_status: str = Field(description="Applicant marital status.")


class PersonalDetailsPatch(Schema):
    application_id: str = Field(
        description="Application containing the personal-details record."
    )
    title: str | None = Field(default=None, description="Replacement applicant title.")
    surname: str | None = Field(
        default=None, description="Replacement applicant surname."
    )
    other_names: str | None = Field(
        default=None, description="Replacement applicant other names."
    )
    id_number: str | None = Field(
        default=None, description="Replacement identity or passport number."
    )
    date_of_birth: date | None = Field(
        default=None, description="Replacement applicant date of birth."
    )
    marital_status: str | None = Field(
        default=None, description="Replacement applicant marital status."
    )


class PersonalDetailsOut(PersonalDetailsIn):
    id: str = Field(description="Unique personal-details record identifier.")
    created_at: datetime = Field(description="Record creation timestamp.")
    updated_at: datetime = Field(description="Record last-update timestamp.")


class PersonalDetailsListOut(Schema):
    total: int = Field(description="Total number of matching personal-details records.")
    data: list[PersonalDetailsOut] = Field(description="Personal-details records.")


class AddressIn(Schema):
    application_id: str = Field(description="Application this address belongs to.")
    postal_address: str = Field(description="Applicant postal address.")
    physical_address: str = Field(
        description="Applicant physical or residential address."
    )
    duration_of_stay: str = Field(
        description="How long the applicant has stayed at the address."
    )


class AddressPatch(Schema):
    application_id: str = Field(
        description="Application containing the address record."
    )
    postal_address: str | None = Field(
        default=None, description="Replacement postal address."
    )
    physical_address: str | None = Field(
        default=None, description="Replacement physical address."
    )
    duration_of_stay: str | None = Field(
        default=None, description="Replacement duration of stay."
    )


class AddressOut(AddressIn):
    id: str = Field(description="Unique address record identifier.")
    created_at: datetime = Field(description="Record creation timestamp.")
    updated_at: datetime = Field(description="Record last-update timestamp.")


class AddressListOut(Schema):
    total: int = Field(description="Total number of matching address records.")
    data: list[AddressOut] = Field(description="Address records.")


class ContactIn(Schema):
    application_id: str = Field(description="Application this contact belongs to.")
    contact_type: str = Field(
        description="Contact type, such as telephone, cell phone, facsimile, or general."
    )
    contact_value: str = Field(description="Phone, fax, or other contact value.")
    email: str = Field(
        description="Contact email address.",
    )


class ContactPatch(Schema):
    application_id: str = Field(
        description="Application containing the contact record."
    )
    contact_type: str | None = Field(
        default=None, description="Replacement contact type."
    )
    contact_value: str | None = Field(
        default=None, description="Replacement contact value."
    )
    email: str | None = Field(
        default=None,
        description="Replacement contact email address.",
    )


class ContactOut(ContactIn):
    id: str = Field(description="Unique contact record identifier.")
    created_at: datetime = Field(description="Record creation timestamp.")
    updated_at: datetime = Field(description="Record last-update timestamp.")


class ContactListOut(Schema):
    total: int = Field(description="Total number of matching contact records.")
    data: list[ContactOut] = Field(description="Contact records.")


class EmploymentIn(Schema):
    application_id: str = Field(
        description="Application this employment record belongs to."
    )
    employer_name: str = Field(description="Name of the applicant's employer.")
    employer_address: str = Field(description="Employer address.")
    job_title: str = Field(description="Applicant job title.")
    salary_per_month: Decimal = Field(
        description="Applicant gross monthly salary.",
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    training_experience: str = Field(
        description="Details of relevant training or experience."
    )
    project_description: str = Field(description="Brief description of the project.")
    ever_applied_for_loan: bool = Field(
        description="Whether the applicant has previously applied for government assistance."
    )
    loan_amount_requested: Decimal = Field(
        description="Amount being requested for the application.",
        ge=0,
        max_digits=10,
        decimal_places=2,
    )


class EmploymentPatch(Schema):
    application_id: str = Field(
        description="Application containing the employment record."
    )
    employer_name: str | None = Field(
        default=None, description="Replacement employer name."
    )
    employer_address: str | None = Field(
        default=None, description="Replacement employer address."
    )
    job_title: str | None = Field(default=None, description="Replacement job title.")
    salary_per_month: Decimal | None = Field(
        default=None,
        description="Replacement gross monthly salary.",
        ge=0,
        max_digits=10,
        decimal_places=2,
    )
    training_experience: str | None = Field(
        default=None, description="Replacement training or experience details."
    )
    project_description: str | None = Field(
        default=None, description="Replacement project description."
    )
    ever_applied_for_loan: bool | None = Field(
        default=None,
        description="Replacement previous-loan-application indicator.",
    )
    loan_amount_requested: Decimal | None = Field(
        default=None,
        description="Replacement requested loan amount.",
        ge=0,
        max_digits=10,
        decimal_places=2,
    )


class EmploymentOut(EmploymentIn):
    id: str = Field(description="Unique employment record identifier.")
    created_at: datetime = Field(description="Record creation timestamp.")
    updated_at: datetime = Field(description="Record last-update timestamp.")


class EmploymentListOut(Schema):
    total: int = Field(description="Total number of matching employment records.")
    data: list[EmploymentOut] = Field(description="Employment records.")
