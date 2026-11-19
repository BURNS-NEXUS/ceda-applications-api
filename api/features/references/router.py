from django.views.decorators.csrf import csrf_exempt
from ninja import Query, Router
from ninja.errors import HttpError

from api.features.applications.models import Application

from .models import NextOfKin, References, ReferencesCommercialBankers
from .schemas import (
    CommercialBankerIn,
    CommercialBankerListOut,
    CommercialBankerOut,
    CommercialBankerPatch,
    DeleteResult,
    NextOfKinIn,
    NextOfKinListOut,
    NextOfKinOut,
    NextOfKinPatch,
    ReferenceIn,
    ReferenceListOut,
    ReferenceOut,
    ReferencePatch,
    ReferenceResourceFilters,
)

router = Router()


def _is_admin(request):
    return request.auth.groups.filter(name="admin").exists()


def _accessible_records(request, model):
    records = model.objects.all()
    if not _is_admin(request):
        records = records.filter(application__owner=request.auth)
    return records


def _list_records(request, model, filters):
    records = _accessible_records(request, model)
    if filters.application_id is not None:
        records = records.filter(application_id=filters.application_id)
    return {"total": records.count(), "data": records.order_by("-created_at", "-id")}


def _get_record(request, model, record_id, application_id=None):
    records = _accessible_records(request, model).filter(id=record_id)
    if application_id is not None:
        records = records.filter(application_id=application_id)
    try:
        return records.get()
    except model.DoesNotExist:
        raise HttpError(404, f"{model.__name__} record not found")


def _get_application(request, application_id):
    applications = Application.objects.all()
    if not _is_admin(request):
        applications = applications.filter(owner=request.auth)
    try:
        return applications.get(id=application_id)
    except Application.DoesNotExist:
        raise HttpError(404, "Application not found")


def _create_record(request, model, payload, check_exist=False):
    values = payload.model_dump()
    application = _get_application(request, values.pop("application_id"))
    # allow at most 2
    if check_exist:
        existing = model.objects.filter(application=application)
        if existing.count() >= 2:
            raise HttpError(
                400, f"{model.__name__} record limit reached for this application"
            )
    return model.objects.create(application=application, **values)


def _update_record(request, model, record_id, payload):
    values = payload.model_dump(exclude_none=True)
    application_id = values.pop("application_id")
    record = _get_record(request, model, record_id, application_id)
    for field, value in values.items():
        setattr(record, field, value)
    record.save()
    return record


@router.get(
    "/references",
    response=ReferenceListOut,
    tags=["References"],
    summary="List personal references",
)
def list_references(request, filters: Query[ReferenceResourceFilters]):
    """List personal references available to the authenticated user, optionally filtered by application."""
    return _list_records(request, References, filters)


@router.post(
    "/references",
    response={201: ReferenceOut},
    tags=["References"],
    summary="Create a personal reference",
)
@csrf_exempt
def create_reference(request, payload: ReferenceIn):
    """Create a personal reference for an owned application. `application_id` is required in the body. At most two records are allowed per application."""
    return 201, _create_record(request, References, payload, check_exist=True)


@router.get(
    "/references/{record_id}",
    response=ReferenceOut,
    tags=["References"],
    summary="Get a personal reference",
)
def get_reference(request, record_id: str):
    """Get one personal reference by its unique record ID."""
    return _get_record(request, References, record_id)


@router.patch(
    "/references/{record_id}",
    response=ReferenceOut,
    tags=["References"],
    summary="Update a personal reference",
)
@csrf_exempt
def update_reference(request, record_id: str, payload: ReferencePatch):
    """Update non-null reference fields. The body must identify the containing application."""
    return _update_record(request, References, record_id, payload)


@router.delete(
    "/references/{record_id}",
    response=DeleteResult,
    tags=["References"],
    summary="Delete a personal reference",
)
def delete_reference(request, record_id: str):
    """Delete a personal reference owned by the authenticated user or an administrator."""
    _get_record(request, References, record_id).delete()
    return {"success": True}


@router.get(
    "/commercial-bankers",
    response=CommercialBankerListOut,
    tags=["Commercial bankers"],
    summary="List commercial-banker references",
)
def list_commercial_bankers(request, filters: Query[ReferenceResourceFilters]):
    """List commercial-banker references available to the authenticated user, optionally filtered by application."""
    return _list_records(request, ReferencesCommercialBankers, filters)


@router.post(
    "/commercial-bankers",
    response={201: CommercialBankerOut},
    tags=["Commercial bankers"],
    summary="Create a commercial-banker reference",
)
@csrf_exempt
def create_commercial_banker(request, payload: CommercialBankerIn):
    """Create commercial-banker and accountant or auditor details. `application_id` is required in the body. At most two records are allowed per application."""
    return 201, _create_record(
        request, ReferencesCommercialBankers, payload, check_exist=True
    )


@router.get(
    "/commercial-bankers/{record_id}",
    response=CommercialBankerOut,
    tags=["Commercial bankers"],
    summary="Get a commercial-banker reference",
)
def get_commercial_banker(request, record_id: str):
    """Get one commercial-banker reference by its unique record ID."""
    return _get_record(request, ReferencesCommercialBankers, record_id)


@router.patch(
    "/commercial-bankers/{record_id}",
    response=CommercialBankerOut,
    tags=["Commercial bankers"],
    summary="Update a commercial-banker reference",
)
@csrf_exempt
def update_commercial_banker(request, record_id: str, payload: CommercialBankerPatch):
    """Update non-null commercial-banker fields. The body must identify the containing application."""
    return _update_record(request, ReferencesCommercialBankers, record_id, payload)


@router.delete(
    "/commercial-bankers/{record_id}",
    response=DeleteResult,
    tags=["Commercial bankers"],
    summary="Delete a commercial-banker reference",
)
def delete_commercial_banker(request, record_id: str):
    """Delete a commercial-banker reference owned by the authenticated user or an administrator."""
    _get_record(request, ReferencesCommercialBankers, record_id).delete()
    return {"success": True}


@router.get(
    "/next-of-kin",
    response=NextOfKinListOut,
    tags=["Next of kin"],
    summary="List next-of-kin records",
)
def list_next_of_kin(request, filters: Query[ReferenceResourceFilters]):
    """List next-of-kin records available to the authenticated user, optionally filtered by application."""
    return _list_records(request, NextOfKin, filters)


@router.post(
    "/next-of-kin",
    response={201: NextOfKinOut},
    tags=["Next of kin"],
    summary="Create a next-of-kin record",
)
@csrf_exempt
def create_next_of_kin(request, payload: NextOfKinIn):
    """Create a next-of-kin record for an owned application. `application_id` is required in the body. At most two records are allowed per application."""
    return 201, _create_record(request, NextOfKin, payload, check_exist=True)


@router.get(
    "/next-of-kin/{record_id}",
    response=NextOfKinOut,
    tags=["Next of kin"],
    summary="Get a next-of-kin record",
)
def get_next_of_kin(request, record_id: str):
    """Get one next-of-kin record by its unique record ID."""
    return _get_record(request, NextOfKin, record_id)


@router.patch(
    "/next-of-kin/{record_id}",
    response=NextOfKinOut,
    tags=["Next of kin"],
    summary="Update a next-of-kin record",
)
@csrf_exempt
def update_next_of_kin(request, record_id: str, payload: NextOfKinPatch):
    """Update non-null next-of-kin fields. The body must identify the containing application."""
    return _update_record(request, NextOfKin, record_id, payload)


@router.delete(
    "/next-of-kin/{record_id}",
    response=DeleteResult,
    tags=["Next of kin"],
    summary="Delete a next-of-kin record",
)
def delete_next_of_kin(request, record_id: str):
    """Delete a next-of-kin record owned by the authenticated user or an administrator."""
    _get_record(request, NextOfKin, record_id).delete()
    return {"success": True}
