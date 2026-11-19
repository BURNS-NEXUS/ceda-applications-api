from django.views.decorators.csrf import csrf_exempt
from ninja import Query, Router
from ninja.errors import HttpError

from api.features.applications.models import Application

from .models import CorporateDetails, ShareHolders
from .schemas import (
    CorporateDetailsIn,
    CorporateDetailsListOut,
    CorporateDetailsOut,
    CorporateDetailsPatch,
    CorporateResourceFilters,
    DeleteResult,
    ShareholderIn,
    ShareholderListOut,
    ShareholderOut,
    ShareholderPatch,
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


def _get_company(request, company_id, application):
    try:
        return _accessible_records(request, CorporateDetails).get(
            id=company_id, application=application
        )
    except CorporateDetails.DoesNotExist:
        raise HttpError(404, "Company record not found for the supplied application")


@router.get(
    "/corporate-details",
    response=CorporateDetailsListOut,
    tags=["Corporate details"],
    summary="List corporate-details records",
)
def list_corporate_details(request, filters: Query[CorporateResourceFilters]):
    """List corporate details available to the authenticated user, optionally filtered by application."""
    return _list_records(request, CorporateDetails, filters)


@router.post(
    "/corporate-details",
    response={201: CorporateDetailsOut},
    tags=["Corporate details"],
    summary="Create corporate details",
)
@csrf_exempt
def create_corporate_details(request, payload: CorporateDetailsIn):
    """Create company details for an owned application. `application_id` is required in the body."""
    values = payload.model_dump()
    application = _get_application(request, values.pop("application_id"))
    return 201, CorporateDetails.objects.create(application=application, **values)


@router.get(
    "/corporate-details/{record_id}",
    response=CorporateDetailsOut,
    tags=["Corporate details"],
    summary="Get corporate details",
)
def get_corporate_details(request, record_id: str):
    """Get one corporate-details record by its unique record ID."""
    return _get_record(request, CorporateDetails, record_id)


@router.patch(
    "/corporate-details/{record_id}",
    response=CorporateDetailsOut,
    tags=["Corporate details"],
    summary="Update corporate details",
)
@csrf_exempt
def update_corporate_details(
    request, record_id: str, payload: CorporateDetailsPatch
):
    """Update non-null company fields. The body must identify the containing application."""
    values = payload.model_dump(exclude_none=True)
    application_id = values.pop("application_id")
    record = _get_record(request, CorporateDetails, record_id, application_id)
    for field, value in values.items():
        setattr(record, field, value)
    record.save()
    return record


@router.delete(
    "/corporate-details/{record_id}",
    response=DeleteResult,
    tags=["Corporate details"],
    summary="Delete corporate details",
)
def delete_corporate_details(request, record_id: str):
    """Delete corporate details owned by the authenticated user or an administrator."""
    _get_record(request, CorporateDetails, record_id).delete()
    return {"success": True}


@router.get(
    "/shareholders",
    response=ShareholderListOut,
    tags=["Shareholders"],
    summary="List shareholder records",
)
def list_shareholders(request, filters: Query[CorporateResourceFilters]):
    """List shareholder records available to the authenticated user, optionally filtered by application."""
    return _list_records(request, ShareHolders, filters)


@router.post(
    "/shareholders",
    response={201: ShareholderOut},
    tags=["Shareholders"],
    summary="Create a shareholder record",
)
@csrf_exempt
def create_shareholder(request, payload: ShareholderIn):
    """Create a shareholder for a company and application. Both IDs are required in the body."""
    values = payload.model_dump()
    application = _get_application(request, values.pop("application_id"))
    company = _get_company(request, values.pop("company_id"), application)
    return 201, ShareHolders.objects.create(
        application=application, company=company, **values
    )


@router.get(
    "/shareholders/{record_id}",
    response=ShareholderOut,
    tags=["Shareholders"],
    summary="Get a shareholder record",
)
def get_shareholder(request, record_id: str):
    """Get one shareholder record by its unique record ID."""
    return _get_record(request, ShareHolders, record_id)


@router.patch(
    "/shareholders/{record_id}",
    response=ShareholderOut,
    tags=["Shareholders"],
    summary="Update a shareholder record",
)
@csrf_exempt
def update_shareholder(request, record_id: str, payload: ShareholderPatch):
    """Update non-null shareholder fields. The body must identify the application and any replacement company."""
    values = payload.model_dump(exclude_none=True)
    application_id = values.pop("application_id")
    shareholder = _get_record(request, ShareHolders, record_id, application_id)
    application = shareholder.application
    if "company_id" in values:
        shareholder.company = _get_company(
            request, values.pop("company_id"), application
        )
    for field, value in values.items():
        setattr(shareholder, field, value)
    shareholder.save()
    return shareholder


@router.delete(
    "/shareholders/{record_id}",
    response=DeleteResult,
    tags=["Shareholders"],
    summary="Delete a shareholder record",
)
def delete_shareholder(request, record_id: str):
    """Delete a shareholder record owned by the authenticated user or an administrator."""
    _get_record(request, ShareHolders, record_id).delete()
    return {"success": True}
