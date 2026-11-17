import django_fsm as fsm
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from ninja import Router
from ninja.errors import HttpError
from ninja.security import django_auth

from .models import Application
from .schemas import ApplicationIn, ApplicationOut

router = Router()


@router.get("/", response=list[ApplicationOut])
def list_applications(request):
    """List all applications for the current user."""
    applications = Application.objects.filter(owner=request.auth)
    return applications


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


@router.put("/{application_id}", response=ApplicationOut)
def update_application(request, application_id: str, payload: ApplicationIn):
    """Update an application."""
    try:
        application = Application.objects.get(id=application_id, owner=request.auth)
        application.project_title = payload.project_title
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


@router.post("/{application_id}/submit", response=ApplicationOut, auth=django_auth)
@csrf_exempt
def submit_application(request, application_id: str):
    """Submit an application."""
    try:
        application = Application.objects.get(id=application_id, owner=request.auth)

        if not fsm.can_proceed(application.submit):
            raise PermissionDenied
        application.submit()
        application.save()
        return application
    except Application.DoesNotExist:
        raise HttpError(404, "Application not found")
    except fsm.TransitionNotAllowed:
        raise HttpError(400, "Application cannot be submitted in its current state")
