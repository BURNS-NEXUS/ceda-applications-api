from datetime import datetime

from ninja import Schema
from pydantic import Field


class ReferenceResourceFilters(Schema):
    """Optional filters shared by reference list endpoints."""

    application_id: str | None = Field(
        default=None,
        description="Restrict results to records belonging to this application.",
    )


class DeleteResult(Schema):
    """Result returned after deleting a reference record."""

    success: bool = Field(description="True when the record was deleted.")


class ReferenceIn(Schema):
    application_id: str = Field(
        description="Application this personal reference belongs to."
    )
    name: str = Field(description="Reference person's full name.")
    postal_address: str = Field(description="Reference person's postal address.")
    cell_phone: str = Field(description="Reference person's cell phone number.")


class ReferencePatch(Schema):
    application_id: str = Field(
        description="Application containing the personal reference."
    )
    name: str | None = Field(
        default=None, description="Replacement reference person's name."
    )
    postal_address: str | None = Field(
        default=None, description="Replacement postal address."
    )
    cell_phone: str | None = Field(
        default=None, description="Replacement cell phone number."
    )


class ReferenceOut(ReferenceIn):
    id: str = Field(description="Unique reference record identifier.")
    created_at: datetime = Field(description="Record creation timestamp.")
    updated_at: datetime = Field(description="Record last-update timestamp.")


class ReferenceListOut(Schema):
    total: int = Field(description="Total number of matching personal references.")
    data: list[ReferenceOut] = Field(description="Personal reference records.")


class CommercialBankerIn(Schema):
    application_id: str = Field(
        description="Application this commercial-banker reference belongs to."
    )
    bank_name: str = Field(description="Commercial bank name.")
    account_number: str = Field(description="Company or applicant bank account number.")
    address: str = Field(description="Commercial bank address.")
    branch: str = Field(description="Commercial bank branch.")
    cell_phone: str = Field(description="Commercial bank contact phone number.")
    accountants_auditor: str = Field(
        description="Name and details of the applicant's accountant or auditor."
    )
    company_name: str = Field(description="Accountant or auditor company name.")
    contact_person: str = Field(description="Accountant or auditor contact person.")
    contact_person_address: str = Field(
        description="Accountant or auditor contact person's address."
    )
    contact_person_cell_phone: str = Field(
        description="Accountant or auditor contact person's cell phone."
    )


class CommercialBankerPatch(Schema):
    application_id: str = Field(
        description="Application containing the commercial-banker reference."
    )
    bank_name: str | None = Field(default=None, description="Replacement bank name.")
    account_number: str | None = Field(
        default=None, description="Replacement bank account number."
    )
    address: str | None = Field(default=None, description="Replacement bank address.")
    branch: str | None = Field(default=None, description="Replacement bank branch.")
    cell_phone: str | None = Field(
        default=None, description="Replacement bank contact phone."
    )
    accountants_auditor: str | None = Field(
        default=None, description="Replacement accountant or auditor details."
    )
    company_name: str | None = Field(
        default=None, description="Replacement accountant or auditor company name."
    )
    contact_person: str | None = Field(
        default=None, description="Replacement accountant or auditor contact person."
    )
    contact_person_address: str | None = Field(
        default=None, description="Replacement contact person's address."
    )
    contact_person_cell_phone: str | None = Field(
        default=None, description="Replacement contact person's cell phone."
    )


class CommercialBankerOut(CommercialBankerIn):
    id: str = Field(description="Unique commercial-banker record identifier.")
    created_at: datetime = Field(description="Record creation timestamp.")
    updated_at: datetime = Field(description="Record last-update timestamp.")


class CommercialBankerListOut(Schema):
    total: int = Field(
        description="Total number of matching commercial-banker records."
    )
    data: list[CommercialBankerOut] = Field(
        description="Commercial-banker reference records."
    )


class NextOfKinIn(Schema):
    application_id: str = Field(
        description="Application this next-of-kin record belongs to."
    )
    name: str = Field(description="Next-of-kin full name.")
    relationship: str = Field(
        description="Relationship of the next of kin to the applicant."
    )
    id_number: str = Field(description="Next-of-kin identity or passport number.")
    postal_address: str = Field(description="Next-of-kin postal address.")
    physical_address: str = Field(description="Next-of-kin physical address.")
    cell_phone: str = Field(description="Next-of-kin cell phone number.")


class NextOfKinPatch(Schema):
    application_id: str = Field(
        description="Application containing the next-of-kin record."
    )
    name: str | None = Field(default=None, description="Replacement full name.")
    relationship: str | None = Field(
        default=None, description="Replacement relationship."
    )
    id_number: str | None = Field(
        default=None, description="Replacement identity or passport number."
    )
    postal_address: str | None = Field(
        default=None, description="Replacement postal address."
    )
    physical_address: str | None = Field(
        default=None, description="Replacement physical address."
    )
    cell_phone: str | None = Field(
        default=None, description="Replacement cell phone number."
    )


class NextOfKinOut(NextOfKinIn):
    id: str = Field(description="Unique next-of-kin record identifier.")
    created_at: datetime = Field(description="Record creation timestamp.")
    updated_at: datetime = Field(description="Record last-update timestamp.")


class NextOfKinListOut(Schema):
    total: int = Field(description="Total number of matching next-of-kin records.")
    data: list[NextOfKinOut] = Field(description="Next-of-kin records.")
