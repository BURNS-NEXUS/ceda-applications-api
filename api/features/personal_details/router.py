from django.views.decorators.csrf import csrf_exempt
from ninja import Query, Router
from ninja.errors import HttpError

from api.features.applications.models import Application

from .models import Address, Contact, Employment, PersonalDetails
from api.features.applications.permissions import (
    can_submit_applications,
    can_view_all_applications,
)
from .schemas import (
    AddressIn,
    AddressListOut,
    AddressOut,
    AddressPatch,
    ApplicantResourceFilters,
    ContactIn,
    ContactListOut,
    ContactOut,
    ContactPatch,
    DeleteResult,
    EmploymentIn,
    EmploymentListOut,
    EmploymentOut,
    EmploymentPatch,
    PersonalDetailsIn,
    PersonalDetailsListOut,
    PersonalDetailsOut,
    PersonalDetailsPatch,
)

router = Router()


def _is_admin(request):
    return request.user.has_perm(f"api.{can_view_all_applications}")


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


def _create_record(request, model, payload, check_exist):
    values = payload.model_dump()
    application = _get_application(request, values.pop("application_id"))
    if check_exist:
        existing = model.objects.filter(application=application)
        if existing.exists():
            raise HttpError(
                400, f"{model.__name__} record already exists for this application"
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
    "/personal-details",
    response=PersonalDetailsListOut,
    tags=["Personal details"],
    summary="List personal-details records",
)
def list_personal_details(request, filters: Query[ApplicantResourceFilters]):
    """List personal-details records available to the authenticated user, optionally filtered by application."""
    return _list_records(request, PersonalDetails, filters)


@router.post(
    "/personal-details",
    response={201: PersonalDetailsOut},
    tags=["Personal details"],
    summary="Create a personal-details record",
)
@csrf_exempt
def create_personal_details(request, payload: PersonalDetailsIn):
    """Create personal details for an owned application. `application_id` is required in the request body."""
    return 201, _create_record(request, PersonalDetails, payload, check_exist=True)


@router.get(
    "/personal-details/{record_id}",
    response=PersonalDetailsOut,
    tags=["Personal details"],
    summary="Get a personal-details record",
)
def get_personal_details(request, record_id: str):
    """Get one personal-details record by its unique record ID."""
    return _get_record(request, PersonalDetails, record_id)


@router.patch(
    "/personal-details/{record_id}",
    response=PersonalDetailsOut,
    tags=["Personal details"],
    summary="Update a personal-details record",
)
@csrf_exempt
def update_personal_details(request, record_id: str, payload: PersonalDetailsPatch):
    """Update non-null personal-details fields. The body must identify the containing application."""
    return _update_record(request, PersonalDetails, record_id, payload)


@router.delete(
    "/personal-details/{record_id}",
    response=DeleteResult,
    tags=["Personal details"],
    summary="Delete a personal-details record",
)
def delete_personal_details(request, record_id: str):
    """Delete a personal-details record owned by the authenticated user or an administrator."""
    _get_record(request, PersonalDetails, record_id).delete()
    return {"success": True}


@router.get(
    "/address",
    response=AddressListOut,
    tags=["Addresses"],
    summary="List address records",
)
def list_addresses(request, filters: Query[ApplicantResourceFilters]):
    """List address records available to the authenticated user, optionally filtered by application."""
    return _list_records(request, Address, filters)


@router.post(
    "/address",
    response={201: AddressOut},
    tags=["Addresses"],
    summary="Create an address record",
)
@csrf_exempt
def create_address(request, payload: AddressIn):
    """Create an address for an owned application. `application_id` is required in the request body."""
    return 201, _create_record(request, Address, payload, check_exist=True)


@router.get(
    "/address/{record_id}",
    response=AddressOut,
    tags=["Addresses"],
    summary="Get an address record",
)
def get_address(request, record_id: str):
    """Get one address record by its unique record ID."""
    return _get_record(request, Address, record_id)


@router.patch(
    "/address/{record_id}",
    response=AddressOut,
    tags=["Addresses"],
    summary="Update an address record",
)
@csrf_exempt
def update_address(request, record_id: str, payload: AddressPatch):
    """Update non-null address fields. The body must identify the containing application."""
    return _update_record(request, Address, record_id, payload)


@router.delete(
    "/address/{record_id}",
    response=DeleteResult,
    tags=["Addresses"],
    summary="Delete an address record",
)
def delete_address(request, record_id: str):
    """Delete an address record owned by the authenticated user or an administrator."""
    _get_record(request, Address, record_id).delete()
    return {"success": True}


@router.get(
    "/contact",
    response=ContactListOut,
    tags=["Contacts"],
    summary="List contact records",
)
def list_contacts(request, filters: Query[ApplicantResourceFilters]):
    """List contact records available to the authenticated user, optionally filtered by application."""
    return _list_records(request, Contact, filters)


@router.post(
    "/contact",
    response={201: ContactOut},
    tags=["Contacts"],
    summary="Create a contact record",
)
@csrf_exempt
def create_contact(request, payload: ContactIn):
    """Create a contact for an owned application. `application_id` is required in the request body."""
    return 201, _create_record(request, Contact, payload, check_exist=True)


@router.get(
    "/contact/{record_id}",
    response=ContactOut,
    tags=["Contacts"],
    summary="Get a contact record",
)
def get_contact(request, record_id: str):
    """Get one contact record by its unique record ID."""
    return _get_record(request, Contact, record_id)


@router.patch(
    "/contact/{record_id}",
    response=ContactOut,
    tags=["Contacts"],
    summary="Update a contact record",
)
@csrf_exempt
def update_contact(request, record_id: str, payload: ContactPatch):
    """Update non-null contact fields. The body must identify the containing application."""
    return _update_record(request, Contact, record_id, payload)


@router.delete(
    "/contact/{record_id}",
    response=DeleteResult,
    tags=["Contacts"],
    summary="Delete a contact record",
)
def delete_contact(request, record_id: str):
    """Delete a contact record owned by the authenticated user or an administrator."""
    _get_record(request, Contact, record_id).delete()
    return {"success": True}


@router.get(
    "/employment",
    response=EmploymentListOut,
    tags=["Employment"],
    summary="List employment records",
)
def list_employment(request, filters: Query[ApplicantResourceFilters]):
    """List employment records available to the authenticated user, optionally filtered by application."""
    return _list_records(request, Employment, filters)


@router.post(
    "/employment",
    response={201: EmploymentOut},
    tags=["Employment"],
    summary="Create an employment record",
)
@csrf_exempt
def create_employment(request, payload: EmploymentIn):
    """Create an employment record for an owned application. `application_id` is required in the request body."""
    return 201, _create_record(request, Employment, payload, check_exist=True)


@router.get(
    "/employment/{record_id}",
    response=EmploymentOut,
    tags=["Employment"],
    summary="Get an employment record",
)
def get_employment(request, record_id: str):
    """Get one employment record by its unique record ID."""
    return _get_record(request, Employment, record_id)


@router.patch(
    "/employment/{record_id}",
    response=EmploymentOut,
    tags=["Employment"],
    summary="Update an employment record",
)
@csrf_exempt
def update_employment(request, record_id: str, payload: EmploymentPatch):
    """Update non-null employment fields. The body must identify the containing application."""
    return _update_record(request, Employment, record_id, payload)


@router.delete(
    "/employment/{record_id}",
    response=DeleteResult,
    tags=["Employment"],
    summary="Delete an employment record",
)
def delete_employment(request, record_id: str):
    """Delete an employment record owned by the authenticated user or an administrator."""
    _get_record(request, Employment, record_id).delete()
    return {"success": True}
