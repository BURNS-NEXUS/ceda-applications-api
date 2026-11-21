import json
import logging
from typing import Literal, Optional

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from ninja import File, Form, Router
from ninja.errors import HttpError
from ninja.files import UploadedFile

ApplicationType = Literal["individual", "company", "all"]
from api.features.applications.models import Application
from api.features.tasks.models import Task
from api.features.tasks.services import is_assigned

from .models import ApplicationDocument, DocumentType
from .schemas import (
    ApplicationDocumentListOut,
    ApplicationDocumentOut,
    DeleteResult,
    DocumentDecisionIn,
    DocumentTypeIn,
    DocumentTypeOut,
    DocumentTypePatch,
    RequiredDocumentListOut,
)
from .services import document_upload_progress
from .validators import validate_document_file

logger = logging.getLogger(__name__)

router = Router()

# Permissions are declared on the models and can be assigned to any user
# independently of groups, roles, or staff status.
PERM_VIEW_ALL_DOCUMENT_TYPES = "api.view_all_document_types"
PERM_MANAGE_DOCUMENT_TYPES = "api.manage_document_types"
PERM_VIEW_ALL_APPLICATION_DOCUMENTS = "api.view_all_application_documents"
PERM_MANAGE_ALL_APPLICATION_DOCUMENTS = "api.manage_all_application_documents"
PERM_REVIEW_APPLICATION_DOCUMENT = "api.review_application_document"


def _has_perm(request, permission):
    user = request.auth
    return bool(user and user.has_perm(permission))


def _require_perm(request, permission):
    if not _has_perm(request, permission):
        raise HttpError(403, "You do not have permission to perform this action.")


def _can_view_inactive_document_types(request):
    return _has_perm(request, PERM_VIEW_ALL_DOCUMENT_TYPES) or _has_perm(
        request, PERM_MANAGE_DOCUMENT_TYPES
    )


def _raise_validation_error(error):
    if hasattr(error, "message_dict"):
        messages = [
            message
            for field_messages in error.message_dict.values()
            for message in field_messages
        ]
    else:
        messages = list(error.messages)
    raise HttpError(400, " ".join(messages) or "Invalid data.")


def _get_application(request, application_id, *permissions):
    if any(_has_perm(request, permission) for permission in permissions):
        applications = Application.objects.all()
    else:
        applications = Application.objects.filter(owner=request.auth)
    try:
        return applications.get(id=application_id)
    except Application.DoesNotExist:
        raise HttpError(404, "Application not found")


def _get_document(request, application, document_id):
    try:
        return (
            ApplicationDocument.objects.select_related(
                "application", "document_type", "rejected_by"
            )
            .filter(application=application)
            .get(id=document_id)
        )
    except ApplicationDocument.DoesNotExist:
        raise HttpError(404, "Document not found")


def _get_document_type(request, document_type_id):
    document_types = DocumentType.objects.all()
    if not _can_view_inactive_document_types(request):
        document_types = document_types.filter(is_active=True)
    try:
        return document_types.get(id=document_type_id)
    except DocumentType.DoesNotExist:
        raise HttpError(404, "Document type not found")


def _absolute_file_url(request, document):
    if not document.file:
        return ""
    try:
        return request.build_absolute_uri(document.file.url)
    except ValueError:
        return ""


def _document_payload(request, document):
    return {
        "id": document.id,
        "application_id": document.application_id,
        "document_type": {
            "id": document.document_type_id,
            "name": document.document_type.name,
        },
        "file": _absolute_file_url(request, document),
        "file_description": document.file_description,
        "status": document.status,
        "reason": document.reason,
        "rejected_by": (
            {
                "id": document.rejected_by_id,
                "username": document.rejected_by.username,
            }
            if document.rejected_by_id
            else None
        ),
        "decision_on": document.decision_on,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


def _validate_upload(file, document_type):
    try:
        validate_document_file(file, document_type.allowed_file_types)
    except ValidationError as error:
        raise HttpError(400, " ".join(error.messages))


def _delete_stored_file(document):
    if not document.file:
        return
    storage = document.file.storage
    name = document.file.name
    try:
        storage.delete(name)
    except OSError:
        logger.warning("Could not delete stored document file %s", name)


@router.get(
    "/document-types",
    response=list[DocumentTypeOut],
    tags=["Document types"],
    summary="List document types",
)
def list_document_types(
    request,
    include_inactive: bool = False,
    application_type: ApplicationType | None = None,
):
    """List active document types.

    Users with ``api.view_all_document_types`` may pass
    ``include_inactive=true`` to also see inactive types.
    """
    if include_inactive and not _can_view_inactive_document_types(request):
        raise HttpError(
            403, "You do not have permission to view inactive document types."
        )

    document_types = DocumentType.objects.all()
    if not include_inactive:
        document_types = document_types.filter(is_active=True)
    if application_type != "all" and application_type is not None:
        document_types = document_types.filter(application_type=application_type)
    return document_types


@router.get(
    "/document-types/{document_type_id}",
    response=DocumentTypeOut,
    tags=["Document types"],
    summary="Get a document type",
)
def get_document_type(request, document_type_id: str):
    """Retrieve an active document type, or any type with the view-all permission."""
    document_types = DocumentType.objects.all()
    if not _can_view_inactive_document_types(request):
        document_types = document_types.filter(is_active=True)
    try:
        return document_types.get(id=document_type_id)
    except DocumentType.DoesNotExist:
        raise HttpError(404, "Document type not found")


@router.post(
    "/document-types",
    response={201: DocumentTypeOut},
    tags=["Document types"],
    summary="Create a document type",
)
@csrf_exempt
def create_document_type(request, payload: DocumentTypeIn):
    """Create a document type. Requires ``api.manage_document_types``."""
    _require_perm(request, PERM_MANAGE_DOCUMENT_TYPES)

    document_type = DocumentType(**payload.model_dump())
    try:
        document_type.full_clean()
        document_type.save()
    except ValidationError as error:
        _raise_validation_error(error)
    return 201, document_type


@router.patch(
    "/document-types/{document_type_id}",
    response=DocumentTypeOut,
    tags=["Document types"],
    summary="Update a document type",
)
@csrf_exempt
def update_document_type(request, document_type_id: str, payload: DocumentTypePatch):
    """Update a document type. Requires ``api.manage_document_types``."""
    _require_perm(request, PERM_MANAGE_DOCUMENT_TYPES)

    try:
        document_type = DocumentType.objects.get(id=document_type_id)
    except DocumentType.DoesNotExist:
        raise HttpError(404, "Document type not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(document_type, field, value)

    try:
        document_type.full_clean()
        document_type.save()
    except ValidationError as error:
        _raise_validation_error(error)
    return document_type


@router.delete(
    "/document-types/{document_type_id}",
    response=DeleteResult,
    tags=["Document types"],
    summary="Delete a document type",
)
@csrf_exempt
def delete_document_type(request, document_type_id: str):
    """Delete an unused document type.

    Requires ``api.manage_document_types``. Types referenced by uploaded
    documents cannot be deleted; deactivate them instead.
    """
    _require_perm(request, PERM_MANAGE_DOCUMENT_TYPES)

    try:
        document_type = DocumentType.objects.get(id=document_type_id)
    except DocumentType.DoesNotExist:
        raise HttpError(404, "Document type not found")

    try:
        document_type.delete()
    except ProtectedError:
        raise HttpError(
            400,
            "This document type is referenced by uploaded documents and cannot "
            "be deleted. Deactivate it instead.",
        )
    return {"success": True}


@router.get(
    "/applications/{application_id}/documents",
    response=ApplicationDocumentListOut,
    tags=["Documents"],
    summary="List application documents",
)
def list_documents(request, application_id: str):
    """List every document uploaded for an application."""
    application = _get_application(
        request,
        application_id,
        PERM_VIEW_ALL_APPLICATION_DOCUMENTS,
        PERM_MANAGE_ALL_APPLICATION_DOCUMENTS,
    )
    documents = application.documents.select_related(
        "document_type", "rejected_by"
    ).order_by("-created_at", "-id")
    return {
        "total": documents.count(),
        "data": [_document_payload(request, document) for document in documents],
    }


@router.get(
    "/applications/{application_id}/documents/required",
    response=RequiredDocumentListOut,
    tags=["Documents"],
    summary="List required document types and upload progress",
)
def list_required_documents(request, application_id: str):
    """Return all active document types and required-document upload progress."""
    application = _get_application(
        request,
        application_id,
        PERM_VIEW_ALL_APPLICATION_DOCUMENTS,
        PERM_MANAGE_ALL_APPLICATION_DOCUMENTS,
    )
    return document_upload_progress(application)


@router.get(
    "/applications/{application_id}/documents/{document_id}",
    response=ApplicationDocumentOut,
    tags=["Documents"],
    summary="Get an application document",
)
def get_document(request, application_id: str, document_id: str):
    """Retrieve a single document belonging to the application."""
    application = _get_application(
        request,
        application_id,
        PERM_VIEW_ALL_APPLICATION_DOCUMENTS,
        PERM_MANAGE_ALL_APPLICATION_DOCUMENTS,
    )
    document = _get_document(request, application, document_id)
    return _document_payload(request, document)


@router.post(
    "/applications/{application_id}/documents",
    response={201: ApplicationDocumentOut},
    tags=["Documents"],
    summary="Upload an application document",
)
@csrf_exempt
def upload_document(
    request,
    application_id: str,
    file: File[UploadedFile],
    document_type_id: str = Form(...),
    file_description: str = Form(""),
):
    """Upload a file for one of the application's document types."""
    application = _get_application(
        request, application_id, PERM_MANAGE_ALL_APPLICATION_DOCUMENTS
    )
    document_type = _get_document_type(request, document_type_id)
    _validate_upload(file, document_type)

    if ApplicationDocument.objects.filter(
        application=application, document_type=document_type
    ).exists():
        raise HttpError(
            400,
            "A document of this type has already been uploaded for this application.",
        )

    try:
        with transaction.atomic():
            document = ApplicationDocument.objects.create(
                application=application,
                document_type=document_type,
                file=file,
                file_description=file_description,
            )
    except IntegrityError:
        raise HttpError(
            400,
            "A document of this type has already been uploaded for this application.",
        )

    return 201, _document_payload(request, document)


@router.patch(
    "/applications/{application_id}/documents/{document_id}",
    response=ApplicationDocumentOut,
    tags=["Documents"],
    summary="Update or replace an application document",
)
@csrf_exempt
def update_document(
    request,
    application_id: str,
    document_id: str,
    file: File[UploadedFile] = None,
    file_description: str | None = Form(None),
):
    """Update the description and/or replace the file.

    Replacing the file re-validates the file type and resets the review status
    to ``pending``.
    """
    application = _get_application(
        request, application_id, PERM_MANAGE_ALL_APPLICATION_DOCUMENTS
    )
    document = _get_document(request, application, document_id)

    # Description-only updates may also be sent as JSON.
    if (
        file is None
        and file_description is None
        and request.content_type == "application/json"
    ):
        try:
            body = json.loads(request.body.decode() or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise HttpError(400, "Invalid JSON body.")
        file_description = body.get("file_description")

    if file is None and file_description is None:
        raise HttpError(400, "No changes were provided.")

    old_storage = None
    old_name = None

    if file is not None:
        _validate_upload(file, document.document_type)
        old_storage = document.file.storage
        old_name = document.file.name
        document.file = file
        document.status = ApplicationDocument.Status.PENDING
        document.reason = ""
        document.rejected_by = None
        document.decision_on = None

    if file_description is not None:
        document.file_description = file_description

    document.save()

    if old_storage and old_name and old_name != document.file.name:
        try:
            old_storage.delete(old_name)
        except OSError:
            logger.warning("Could not delete replaced document file %s", old_name)

    return _document_payload(request, document)


@router.delete(
    "/applications/{application_id}/documents/{document_id}",
    response=DeleteResult,
    tags=["Documents"],
    summary="Delete an application document",
)
@csrf_exempt
def delete_document(request, application_id: str, document_id: str):
    """Delete a document and its stored file."""
    application = _get_application(
        request, application_id, PERM_MANAGE_ALL_APPLICATION_DOCUMENTS
    )
    document = _get_document(request, application, document_id)
    _delete_stored_file(document)
    document.delete()
    return {"success": True}


@router.post(
    "/applications/{application_id}/documents/{document_id}/decision",
    response=ApplicationDocumentOut,
    tags=["Documents"],
    summary="Accept or reject an application document",
)
@csrf_exempt
def decide_document(
    request,
    application_id: str,
    document_id: str,
    payload: DocumentDecisionIn,
):
    """Record a review decision for a document.

    Re-decisions are allowed; ``decision_on`` is always refreshed. ``rejected_by``
    is only set when the document is rejected.
    """
    _require_perm(request, PERM_REVIEW_APPLICATION_DOCUMENT)

    try:
        application = Application.objects.get(id=application_id)
        verification_task = (
            Task.objects.filter(
                application=application,
                task_type=Task.Type.VERIFICATION,
                status__in=[Task.Status.PENDING, Task.Status.ASSIGNED],
            )
            .order_by("-created_at")
            .first()
        )
        if not is_assigned(verification_task, request.auth):
            raise HttpError(403, "Verification task is not assigned to you.")
    except Application.DoesNotExist:
        raise HttpError(404, "Application not found")
    document = _get_document(request, application, document_id)

    reason = (payload.reason or "").strip()
    if payload.status == ApplicationDocument.Status.REJECTED and not reason:
        raise HttpError(400, "A reason is required when a document is rejected.")

    document.status = payload.status
    document.reason = reason
    document.rejected_by = (
        request.auth if payload.status == ApplicationDocument.Status.REJECTED else None
    )
    document.decision_on = timezone.now()
    document.save()
    return _document_payload(request, document)
