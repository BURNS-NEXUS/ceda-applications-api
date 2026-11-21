import django_fsm as fsm
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from ninja import Query, Router
from ninja.errors import HttpError
from ninja.security import django_auth

from api.features.clarifications.models import Clarification
from api.features.documents.models import ApplicationDocument
from api.features.documents.services import document_upload_progress
from api.features.tasks.models import Task
from api.features.tasks.services import ensure_task_for_application, is_assigned

from .filters import ApplicationFilters
from .models import Application
from .permissions import (
    can_submit_applications,
    can_verify_applications,
    can_view_all_applications,
)
from .schemas import (
    ApplicationDetailOut,
    ApplicationIn,
    ApplicationListOut,
    ApplicationOut,
    ApplicationPatch,
    FeedbackApplicationIn,
)

router = Router()


@router.get("/", response=ApplicationListOut)
def list_applications(request, filters: Query[ApplicationFilters]):
    """List all applications for the current user."""
    if filters.assigned_to_me:  # noqa: SIM114
        applications = Application.objects.all()
    elif request.user.has_perm(f"api.{can_view_all_applications}"):
        applications = Application.objects.all()
    else:
        applications = Application.objects.filter(owner=request.auth)
    applications = filters.apply(applications, request.auth)
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


@router.get("/{application_id}", response=ApplicationDetailOut)
def get_application(request, application_id: str):
    """Get a specific application."""
    try:
        application = Application.objects.prefetch_related(
            "personaldetails_set",
            "address_set",
            "contact_set",
            "employment_set",
            "corporatedetails_set",
            "shareholders_set",
            "loans_set",
            "references_set",
            "referencescommercialbankers_set",
            "nextofkin_set",
            "evaluations__scores",
            "clarifications",
        ).filter(id=application_id)
        is_owner = application.filter(owner=request.auth).exists()
        can_view_all = request.auth.has_perm(f"api.{can_view_all_applications}")
        is_assigned = application.filter(
            tasks__assignments__employee=request.auth,
            tasks__assignments__is_active=True,
            tasks__status__in=["pending", "assigned"],
        ).exists()
        if not (is_owner or can_view_all or is_assigned):
            raise Application.DoesNotExist
        application = application.distinct().get()
        return {
            **{
                field: getattr(application, field)
                for field in (
                    "id",
                    "project_title",
                    "state",
                    "company_no",
                    "incorporation_date",
                    "contact_person",
                    "telephone",
                    "business_nature",
                    "business_location",
                    "loan_amount",
                    "email",
                    "has_current_loan_with_other",
                    "has_past_loan_with_other",
                )
            },
            "personal_details": application.personaldetails_set.all(),
            "addresses": application.address_set.all(),
            "contacts": application.contact_set.all(),
            "employments": application.employment_set.all(),
            "corporate_details": application.corporatedetails_set.all(),
            "shareholders": application.shareholders_set.all(),
            "loans": application.loans_set.all(),
            "references": application.references_set.all(),
            "commercial_bankers": application.referencescommercialbankers_set.all(),
            "next_of_kin": application.nextofkin_set.all(),
            "evaluations": application.evaluations.all(),
            "clarifications": application.clarifications.all(),
        }
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
        if payload.has_current_loan_with_other is not None:
            application.has_current_loan_with_other = (
                payload.has_current_loan_with_other
            )
        if payload.has_past_loan_with_other is not None:
            application.has_past_loan_with_other = payload.has_past_loan_with_other
        if payload.application_type is not None:
            application.application_type = payload.application_type
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
    description=(
        "Submit an application from draft state. The application must be in a state that allows submission.\n\n"
        "Requires authentication. \n"
    ),
)
@csrf_exempt
def submit_application(request, application_id: str):
    """Submit an application from draft."""
    try:
        application = Application.objects.get(id=application_id, owner=request.auth)
        application.submission_count += 1
        if not fsm.can_proceed(application.submit):
            raise PermissionDenied
        if not request.user.has_perm(f"api.{can_submit_applications}"):
            raise PermissionDenied
        document_progress = document_upload_progress(application)
        if not document_progress["all_required_uploaded"]:
            raise HttpError(
                422,
                "All required documents must be uploaded before submission. "
                f"Missing: {', '.join(document_progress['missing_required'])}.",
            )
        application.submit(actor=request.auth)
        application.save()
        ensure_task_for_application(application)
        return application
    except Application.DoesNotExist:
        raise HttpError(404, "Application not found")
    except fsm.TransitionNotAllowed:
        raise HttpError(400, "Application cannot be submitted in its current state")
    except PermissionDenied:
        raise HttpError(
            422,
            "Submission failed: You do not have permission to submit this application.",
        )


@router.post(
    "/{application_id}/wf/verify",
    response=ApplicationOut,
    auth=django_auth,
    tags=["Application workflows"],
    description=(
        "Verify an application from submission state. The application must be in a state that allows verification.\n\n"
        "Requires authentication. \n"
    ),
)
@csrf_exempt
def verify_application(request, application_id: str):
    """Verify an application and open its evaluation task."""
    try:
        application = Application.objects.get(id=application_id)
        if not request.user.has_perm(f"api.{can_verify_applications}"):
            raise PermissionDenied
        if not fsm.can_proceed(application.verify):
            raise HttpError(400, "Application cannot be verified in its current state")
        task = Task.objects.filter(
            application=application,
            task_type=Task.Type.VERIFICATION,
            status__in=[Task.Status.PENDING, Task.Status.ASSIGNED],
        ).first()
        if not is_assigned(task, request.auth):
            raise HttpError(403, "You are not assigned to verify this application")
        not_accepted = application.documents.exclude(
            status=ApplicationDocument.Status.ACCEPTED
        ).count()
        if not_accepted:
            raise HttpError(
                422,
                "All documents must be accepted before verification. "
                f"{not_accepted} document(s) are pending or rejected.",
            )
        with transaction.atomic():
            application.verify(actor=request.auth)
            application.save()
            # Completes the verification task and creates/assigns the evaluation
            # task using the evaluators_per_application system setting.
            ensure_task_for_application(application)
        return application
    except Application.DoesNotExist:
        raise HttpError(404, "Application not found")
    except fsm.TransitionNotAllowed:
        raise HttpError(400, "Application cannot be verified in its current state")
    except PermissionDenied:
        raise HttpError(
            403,
            "Verification failed: You do not have permission to verify this application.",
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
        document_progress = document_upload_progress(application)
        if not document_progress["all_required_uploaded"]:
            raise HttpError(
                422,
                "All required documents must be uploaded before resubmission. "
                f"Missing: {', '.join(document_progress['missing_required'])}.",
            )
        with transaction.atomic():
            application.resubmit(actor=request.auth)
            application.save()
            ensure_task_for_application(application)
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
def request_feedback(request, application_id: str, payload: FeedbackApplicationIn):
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
        with transaction.atomic():
            application.request_feedback(actor=request.auth)
            clarification.save()
            application.save()
        return application
    except Application.DoesNotExist:
        raise HttpError(404, "Application not found")
    except fsm.TransitionNotAllowed:
        print(application.state)
        raise HttpError(
            400, "Application cannot be requested for feedback in its current state"
        )
    except PermissionDenied:
        raise HttpError(
            422,
            "Feedback request failed: Application may be in a state that does not allow feedback submission.",
        )
