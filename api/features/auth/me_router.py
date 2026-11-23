from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from ninja import Router
from ninja.errors import HttpError

from .helpers import check_is_email
from .schemas import UserOut, UserPatchIn, UserPermissionsOut

router = Router()


@router.get(
    "/permissions",
    response=UserPermissionsOut,
    tags=["Auth"],
    summary="List the current user's permissions",
)
def get_my_permissions(request):
    """Return every permission granted to the authenticated user.

    Permissions are resolved by Django's authentication backends and include
    permissions granted directly to the user as well as through groups.
    Superusers receive all permissions.
    """
    user = request.auth
    return {
        "user_id": user.id,
        "username": user.username,
        "is_superuser": user.is_superuser,
        "permissions": sorted(user.get_all_permissions()),
    }


@router.patch("", response=UserOut)
@csrf_exempt
def update_me(request, payload: UserPatchIn):
    """Update the current user's display name and email."""
    user = request.auth
    if payload.email is not None:
        email = payload.email.strip()
        if not check_is_email(email):
            raise HttpError(422, "Invalid email format")
        if (
            get_user_model()
            .objects.filter(username__iexact=email)
            .exclude(pk=user.pk)
            .exists()
        ):
            raise HttpError(409, "Email already in use")
        # Registration uses the email as the login username; keep them in sync.
        user.email = email
        user.username = email
    if payload.first_name is not None:
        user.first_name = payload.first_name.strip()
    if payload.last_name is not None:
        user.last_name = payload.last_name.strip()
    user.save(update_fields=["username", "email", "first_name", "last_name"])
    return user
