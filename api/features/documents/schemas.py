from datetime import datetime
from typing import Literal

from ninja import Schema
from pydantic import Field


class DocumentTypeOut(Schema):
    id: str
    name: str
    description: str
    allowed_file_types: list[str]
    is_required: bool
    is_active: bool


class DocumentTypeIn(Schema):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    allowed_file_types: list[str] = Field(min_length=1)
    is_required: bool = True
    is_active: bool = True


class DocumentTypePatch(Schema):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    allowed_file_types: list[str] | None = Field(default=None, min_length=1)
    is_required: bool | None = None
    is_active: bool | None = None


class DocumentTypeRefOut(Schema):
    id: str
    name: str


class RejectedByOut(Schema):
    id: str
    username: str


class ApplicationDocumentOut(Schema):
    id: str
    application_id: str
    document_type: DocumentTypeRefOut
    file: str
    file_description: str
    status: str
    reason: str
    rejected_by: RejectedByOut | None = None
    decision_on: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ApplicationDocumentListOut(Schema):
    total: int
    data: list[ApplicationDocumentOut]


class ApplicationDocumentCreate(Schema):
    """Metadata for a document upload.

    Files are sent as multipart form data, not JSON.
    """

    document_type_id: str
    file: str = Field(description="Document file (multipart upload)")
    file_description: str = ""


class ApplicationDocumentUpdate(Schema):
    """Optional document fields for a multipart PATCH request."""

    file: str | None = Field(
        default=None, description="Replacement document file (multipart upload)"
    )
    file_description: str | None = None


class DocumentDecisionIn(Schema):
    status: Literal["accepted", "rejected"]
    reason: str | None = Field(default=None, max_length=5000)


class RequiredDocumentOut(DocumentTypeOut):
    uploaded: bool
    document_id: str | None = None
    status: str | None = None


class RequiredDocumentListOut(Schema):
    total: int
    data: list[RequiredDocumentOut]
    all_required_uploaded: bool
    missing_required: list[str]


class DeleteResult(Schema):
    success: bool
