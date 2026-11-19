"""Validation helpers for application document uploads."""

import os

from django.conf import settings
from django.core.exceptions import ValidationError

# Document type "families" and the file extensions they allow.
DOCUMENT_FILE_TYPE_EXTENSIONS = {
    "pdf": {".pdf"},
    "img": {".jpg", ".jpeg", ".png"},
}

DOCUMENT_FILE_TYPE_CHOICES = [
    ("pdf", "PDF"),
    ("img", "Image (JPG, JPEG, PNG)"),
]

DOCUMENT_FILE_TYPE_LABELS = dict(DOCUMENT_FILE_TYPE_CHOICES)

DEFAULT_MAX_DOCUMENT_FILE_SIZE = 10 * 1024 * 1024


def max_document_file_size():
    return getattr(
        settings, "MAX_DOCUMENT_FILE_SIZE", DEFAULT_MAX_DOCUMENT_FILE_SIZE
    )


def file_extension(filename):
    """Return the lower-cased extension of a filename, including the dot."""
    return os.path.splitext(filename or "")[1].lower()


def allowed_extensions(allowed_file_types):
    """Expand a list of document type families into concrete file extensions."""
    extensions = set()
    for file_type in allowed_file_types or []:
        extensions.update(DOCUMENT_FILE_TYPE_EXTENSIONS.get(file_type, set()))
    return extensions


def validate_allowed_file_types(allowed_file_types):
    """Validate the values stored on ``DocumentType.allowed_file_types``."""
    if not allowed_file_types:
        raise ValidationError("At least one allowed file type must be selected.")

    invalid = set(allowed_file_types) - set(DOCUMENT_FILE_TYPE_EXTENSIONS)
    if invalid:
        raise ValidationError(
            "Invalid file type(s): "
            f"{', '.join(sorted(invalid))}. "
            f"Allowed values are: {', '.join(DOCUMENT_FILE_TYPE_EXTENSIONS)}."
        )


def validate_file_size(file):
    """Reject uploads above the configured maximum file size."""
    if file is None:
        return

    try:
        size = getattr(file, "size", None)
    except (OSError, ValueError):
        # The underlying file is unavailable; nothing to validate.
        return

    if size is not None and size > max_document_file_size():
        max_mb = max_document_file_size() / (1024 * 1024)
        raise ValidationError(
            f"File size must not exceed {max_mb:g}MB."
        )


def validate_document_file(file, allowed_file_types):
    """Validate a file against a document type's allowed file types and size."""
    validate_file_size(file)

    extensions = allowed_extensions(allowed_file_types)
    extension = file_extension(getattr(file, "name", None))
    if extension not in extensions:
        allowed = ", ".join(sorted(extensions)) or "no file types configured"
        raise ValidationError(
            f"File type '{extension or 'unknown'}' is not allowed. "
            f"Allowed extensions: {allowed}."
        )
