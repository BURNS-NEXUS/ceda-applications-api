from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from ninja import Router
from ninja.errors import HttpError

from .models import Absentee
from .schemas import AbsenteeCreateIn, AbsenteeOut, DeleteResult

router = Router()

# Django automatically creates add/change/delete/view permissions for every
# model; the codenames below are the ones guarding the absentee endpoints.
PERM_ADD_ABSENTEE = "api.add_absentee"
PERM_DELETE_ABSENTEE = "api.delete_absentee"


def _require_perm(request, permission):
    if not request.auth.has_perm(permission):
        raise HttpError(403, "You do not have permission to perform this action.")


def _absentee_out(absentee: Absentee) -> AbsenteeOut:
    return AbsenteeOut(
        id=absentee.id,
        user_id=absentee.user_id,
        username=absentee.user.username,
        leave_type=absentee.leave_type,
        start_date=absentee.start_date,
        end_date=absentee.end_date,
        reason=absentee.reason,
        is_on_leave=absentee.is_on_leave,
        created_at=absentee.created_at,
        updated_at=absentee.updated_at,
    )


@router.get(
    "/",
    response=list[AbsenteeOut],
    tags=["Absentees"],
    summary="List absentees",
    operation_id="listAbsentees",
    description=(
        "List all employee absences tracked by the application.\n\n"
        "Each entry includes the employee (`user_id` and `username`), the "
        "`leave_type`, the leave period (`start_date`/`end_date`) and a "
        "`is_on_leave` flag that is true when today falls within the leave "
        "period.\n\n"
        "Requires authentication."
    ),
)
def list_absentees(request):
    absentees = Absentee.objects.select_related("user").order_by("-created_at")
    return [_absentee_out(absentee) for absentee in absentees]


@router.post(
    "/",
    response={201: AbsenteeOut},
    tags=["Absentees"],
    summary="Add an absentee (record an absence)",
    operation_id="createAbsentee",
    description=(
        "Add an employee to the absentees list, recording the leave they are "
        "taking.\n\n"
        "The leave period is `start_date` (inclusive) and `end_date` "
        "(exclusive of nothing; inclusive). When `end_date` is omitted the "
        "leave is treated as open-ended. Adding an absence for a user who "
        "already has one replaces the previous absence.\n\n"
        "**Permissions**\n"
        "Requires the `api.add_absentee` Django permission. No staff status or "
        "group membership is required; assign the permission directly to a user "
        "or through a group.\n\n"
        "**Validation**\n"
        "- `start_date` must not be after `end_date`.\n"
        "- `leave_type` must be one of: `vacation`, `sick`, `personal`, `unpaid`, `other`.\n\n"
        "Returns the stored absentee with its `is_on_leave` flag."
    ),
)
@csrf_exempt
def create_absentee(request, payload: AbsenteeCreateIn):
    _require_perm(request, PERM_ADD_ABSENTEE)

    User = get_user_model()
    try:
        user = User.objects.get(id=payload.user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found")

    absentee = Absentee.objects.filter(user=user).first()
    if absentee is None:
        absentee = Absentee(user=user)

    absentee.leave_type = payload.leave_type
    absentee.start_date = payload.start_date
    absentee.end_date = payload.end_date
    absentee.reason = payload.reason or ""

    try:
        absentee.full_clean()
        absentee.save()
    except ValidationError as error:
        if hasattr(error, "message_dict"):
            messages = [
                message
                for field_messages in error.message_dict.values()
                for message in field_messages
            ]
        else:
            messages = list(error.messages)
        raise HttpError(400, " ".join(messages) or "Invalid absentee data.")

    return 201, _absentee_out(absentee)


@router.delete(
    "/{absentee_id}",
    response=DeleteResult,
    tags=["Absentees"],
    summary="Remove an absentee",
    operation_id="deleteAbsentee",
    description=(
        "Remove an employee's absence record so they are no longer tracked as "
        "absent.\n\n"
        "**Permissions**\n"
        "Requires the `api.delete_absentee` Django permission. No staff status "
        "or group membership is required; assign the permission directly to a "
        "user or through a group.\n\n"
        "Returns `{\"success\": true}` on success."
    ),
)
@csrf_exempt
def delete_absentee(request, absentee_id: str):
    _require_perm(request, PERM_DELETE_ABSENTEE)

    try:
        absentee = Absentee.objects.get(id=absentee_id)
    except Absentee.DoesNotExist:
        raise HttpError(404, "Absentee not found")

    absentee.delete()
    return {"success": True}
