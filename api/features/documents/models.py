import os

from cuid2 import Cuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .permissions import (
    manage_document_types,
    view_all_document_types,
)
from .validators import (
    DOCUMENT_FILE_TYPE_LABELS,
    allowed_extensions,
    validate_allowed_file_types,
    validate_document_file,
)

_cuid = Cuid()


def generate_cuid():
    return _cuid.generate()


def application_document_upload_path(instance, filename):
    """Store uploads under ``applications/<application_id>/documents/``."""
    filename = os.path.basename(filename)
    return f"applications/{instance.application_id}/documents/{filename}"


class DocumentType(models.Model):
    """Admin-managed catalog of document types applicants can upload."""

    id = models.CharField(
        primary_key=True, max_length=32, default=generate_cuid, editable=False
    )
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    allowed_file_types = models.JSONField(
        default=list,
        help_text="File type families accepted for this document (pdf, img).",
    )
    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive document types are hidden from applicants.",
    )
    application_type = models.CharField(
        max_length=255,
        choices=[
            ("individual", "Individual"),
            ("company", "Company"),
            ("all", "All"),
        ],
        default="all",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]  # noqa: RUF012
        verbose_name = "Document type"
        verbose_name_plural = "Document types"
        permissions = [  # noqa: RUF012
            (
                view_all_document_types,
                "Can view inactive document types",
            ),
            (
                manage_document_types,
                "Can create, update, and delete document types",
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        validate_allowed_file_types(self.allowed_file_types)

    @property
    def allowed_file_types_display(self):
        return ", ".join(
            DOCUMENT_FILE_TYPE_LABELS.get(value, value)
            for value in self.allowed_file_types or []
        )

    @property
    def allowed_extensions(self):
        return allowed_extensions(self.allowed_file_types)


class ApplicationDocument(models.Model):
    """A file uploaded by an applicant against an application."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    id = models.CharField(
        primary_key=True, max_length=32, default=generate_cuid, editable=False
    )
    application = models.ForeignKey(
        "api.Application",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.PROTECT,
        related_name="documents",
    )
    file = models.FileField(upload_to=application_document_upload_path)
    file_description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    reason = models.TextField(blank=True)
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="document_decisions",
    )
    decision_on = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012
        verbose_name = "Application document"
        verbose_name_plural = "Application documents"
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["application", "document_type"],
                name="unique_document_per_application_type",
            )
        ]
        permissions = [  # noqa: RUF012
            (
                "view_all_application_documents",
                "Can view documents for any application",
            ),
            (
                "manage_all_application_documents",
                "Can upload, replace, and delete documents for any application",
            ),
            (
                "review_application_document",
                "Can accept or reject application documents",
            ),
        ]

    def __str__(self):
        return f"{self.document_type} for {self.application}"

    def clean(self):
        super().clean()

        if self.status == self.Status.REJECTED and not (self.reason or "").strip():
            raise ValidationError(
                {"reason": "A reason is required when a document is rejected."}
            )

        if self.document_type_id and self.file:
            try:
                validate_document_file(self.file, self.document_type.allowed_file_types)
            except ValidationError as error:
                raise ValidationError({"file": error.messages}) from error
