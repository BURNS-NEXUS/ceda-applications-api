from ninja import Router

from .schemas import UserPermissionsOut

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
