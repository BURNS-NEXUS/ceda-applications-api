from django.views.decorators.csrf import csrf_exempt
from ninja import Query, Router
from ninja.errors import HttpError

from api.features.applications.models import Application

from .models import Loans
from .schemas import (
    DeleteResult,
    FinancialDetailsFilters,
    LoanIn,
    LoanListOut,
    LoanOut,
    LoanPatch,
)

router = Router()


def _is_admin(request):
    return request.auth.groups.filter(name="admin").exists()


def _accessible_loans(request):
    loans = Loans.objects.all()
    if not _is_admin(request):
        loans = loans.filter(application__owner=request.auth)
    return loans


def _get_application(request, application_id):
    applications = Application.objects.all()
    if not _is_admin(request):
        applications = applications.filter(owner=request.auth)
    try:
        return applications.get(id=application_id)
    except Application.DoesNotExist:
        raise HttpError(404, "Application not found")


def _get_loan(request, record_id, application_id=None):
    loans = _accessible_loans(request).filter(id=record_id)
    if application_id is not None:
        loans = loans.filter(application_id=application_id)
    try:
        return loans.get()
    except Loans.DoesNotExist:
        raise HttpError(404, "Loan record not found")


@router.get(
    "/loans",
    response=LoanListOut,
    tags=["Financial details"],
    summary="List loan records",
)
def list_loans(request, filters: Query[FinancialDetailsFilters]):
    """List loan records available to the authenticated user, optionally filtered by application."""
    loans = _accessible_loans(request)
    if filters.application_id is not None:
        loans = loans.filter(application_id=filters.application_id)
    return {"total": loans.count(), "data": loans.order_by("-created_at", "-id")}


@router.post(
    "/loans",
    response={201: LoanOut},
    tags=["Financial details"],
    summary="Create a loan record",
)
@csrf_exempt
def create_loan(request, payload: LoanIn):
    """Create loan details for an owned application. `application_id` is required in the body."""
    values = payload.model_dump()
    application = _get_application(request, values.pop("application_id"))
    return 201, Loans.objects.create(application=application, **values)


@router.get(
    "/loans/{record_id}",
    response=LoanOut,
    tags=["Financial details"],
    summary="Get a loan record",
)
def get_loan(request, record_id: str):
    """Get one loan record by its unique record ID."""
    return _get_loan(request, record_id)


@router.patch(
    "/loans/{record_id}",
    response=LoanOut,
    tags=["Financial details"],
    summary="Update a loan record",
)
@csrf_exempt
def update_loan(request, record_id: str, payload: LoanPatch):
    """Update non-null loan fields. The body must identify the containing application."""
    values = payload.model_dump(exclude_none=True)
    application_id = values.pop("application_id")
    loan = _get_loan(request, record_id, application_id)
    for field, value in values.items():
        setattr(loan, field, value)
    loan.save()
    return loan


@router.delete(
    "/loans/{record_id}",
    response=DeleteResult,
    tags=["Financial details"],
    summary="Delete a loan record",
)
def delete_loan(request, record_id: str):
    """Delete a loan record owned by the authenticated user or an administrator."""
    _get_loan(request, record_id).delete()
    return {"success": True}
