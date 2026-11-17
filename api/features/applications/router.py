import django_fsm as fsm
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from ninja import Query, Router
from ninja.errors import HttpError
from ninja.security import django_auth

from api.features.clarifications.models import Clarification

from .filters import ApplicationFilters
from .models import Application
from .schemas import (
    ApplicationIn,
    ApplicationListOut,
    ApplicationOut,
    ApplicationPatch,
    FeebackAplicationIn,
)

router = Router()


@router.get("/", response=ApplicationListOut)
def list_applications(request, filters: Query[ApplicationFilters]):
    """List all applications for the current user."""
    groups = list(request.auth.groups.values_list("name", flat=True))
    if "admin" in groups:
        applications = Application.objects.all()
    else:
        applications = Application.objects.filter(owner=request.auth)
    applications = filters.apply(applications)
    total = applications.count()
    applications = applications.order_by("-created_at", "-id")
    stop = filters.skip + filters.take if filters.take is not None else None
    return {"total": total, "data": applications[filters.skip : stop]}


@router.post("/", response={201: ApplicationOut}, auth=django_auth)
@csrf_exempt
def create_application(request, payload: ApplicationIn):
    """Create a new application."""
    application = Application.objects.create(owner=request.auth, **payload.dict())
    return application


@router.get("/{application_id}", response=ApplicationOut)
def get_application(request, application_id: str):
    """Get a specific application."""
    try:
        application = Application.objects.get(id=application_id, owner=request.auth)
        return application
    except Application.DoesNotExist:
        raise HttpError(404, "Application not found")


@router.patch("/{application_id}", response=ApplicationOut)
@csrf_exempt
def update_application(request, application_id: str, payload: ApplicationPatch):
    """Update an application."""
    try:
        application = Application.objects.get(id=application_id)
        user = request.auth
        groups = list(user.groups.values_list("name", flat=True))
        if (
            application.state not in ["draft", "feedback"]
            and application.owner != user
            and ["admin"] not in groups
        ):
            raise HttpError(
                403, "You do not have permission to update this application"
            )
        if payload.project_title is not None:
            application.project_title = payload.project_title
        if payload.company_no is not None:
            application.company_no = payload.company_no
        if payload.incorporation_date is not None:
            application.incorporation_date = payload.incorporation_date
        if payload.contact_person is not None:
            application.contact_person = payload.contact_person
        if payload.telephone is not None:
            application.telephone = payload.telephone
        if payload.business_nature is not None:
            application.business_nature = payload.business_nature
        if payload.business_location is not None:
            application.business_location = payload.business_location
        if payload.loan_amount is not None:
            application.loan_amount = payload.loan_amount
        if payload.email is not None:
            application.email = payload.email
        application.save()
        return application
    except Application.DoesNotExist:
        raise HttpError(404, "Application not found")


@router.delete("/{application_id}", response=dict)
def delete_application(request, application_id: str):
    """Delete an application."""
    try:
        application = Application.objects.get(id=application_id, owner=request.auth)
        application.delete()
        return {"success": True}
    except Application.DoesNotExist:
        raise HttpError(404, "Application not found")


@router.post(
    "/{application_id}/wf/submit",
    response=ApplicationOut,
    auth=django_auth,
    tags=["Application workflows"],
)
@csrf_exempt
def submit_application(request, application_id: str):
    """Submit an application from draft."""
    try:
        application = Application.objects.get(id=application_id, owner=request.auth)
        application.submission_count += 1

        if not fsm.can_proceed(application.submit):
            raise PermissionDenied
        application.submit()
        application.save()
        return application
    except Application.DoesNotExist:
        raise HttpError(404, "Application not found")
    except fsm.TransitionNotAllowed:
        raise HttpError(400, "Application cannot be submitted in its current state")
    except PermissionDenied:
        raise HttpError(
            422,
            "Submission failed: Application may be in a state that does not allow submission.",
        )


@router.post(
    "/{application_id}/wf/resubmit",
    response=ApplicationOut,
    auth=django_auth,
    tags=["Application workflows"],
)
@csrf_exempt
def resubmit_application(request, application_id: str):
    """Resubmit an application."""
    try:
        application = Application.objects.get(id=application_id, owner=request.auth)
        application.submission_count += 1

        if not fsm.can_proceed(application.resubmit):
            raise PermissionDenied
        application.resubmit()
        application.save()
        return application
    except Application.DoesNotExist:
        raise HttpError(404, "Application not found")
    except fsm.TransitionNotAllowed:
        raise HttpError(400, "Application cannot be resubmitted in its current state")
    except PermissionDenied:
        raise HttpError(
            422,
            "Resubmission failed: Application may be in a state that does not allow resubmission.",
        )


@router.post(
    "/{application_id}/wf/feedback",
    response=ApplicationOut,
    auth=django_auth,
    tags=["Application workflows"],
)
@csrf_exempt
def request_feedback(request, application_id: str, payload: FeebackAplicationIn):
    """Reject an application by requesting feedback from applicant"""
    try:
        application = Application.objects.get(id=application_id, owner=request.auth)
        if not fsm.can_proceed(application.request_feedback):
            raise PermissionDenied
        clarification = Clarification.objects.create(
            **payload.dict(),
            application_id=application_id,
            version=application.submission_count,
            created_by=request.auth,
        )
        application.request_feedback()
        clarification.save()
        application.save()
        return application
    except Application.DoesNotExist:
        raise HttpError(404, "Application not found")
    except fsm.TransitionNotAllowed:
        print(application.state)
        raise HttpError(400, "Application cannot be submitted in its current state")
    except PermissionDenied:
        raise HttpError(
            422,
            "Submission failed: Application may be in a state that does not allow feedback submission.",
        )
