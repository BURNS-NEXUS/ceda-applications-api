from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from ninja import Router
from ninja.errors import HttpError

from .models import SystemSettings
from .schemas import SettingsIn, SettingsOut

router = Router()

PERM_CHANGE_SYSTEM_SETTINGS = "api.change_systemsettings"


def _raise_validation_error(error):
    if hasattr(error, "message_dict"):
        messages = [
            message
            for field_messages in error.message_dict.values()
            for message in field_messages
        ]
    else:
        messages = list(error.messages)
    raise HttpError(400, " ".join(messages) or "Invalid settings.")


@router.get(
    "/settings",
    response=SettingsOut,
    tags=["Single types"],
    summary="Get system settings",
    operation_id="getSystemSettings",
    description=(
        "Return the application's singleton system settings.\n\n"
        "The settings record is created with default values the first time it "
        "is requested. Any authenticated user may read these values so clients "
        "can display the site name and respect maintenance mode.\n\n"
        "**Fields**\n"
        "- `site_name` — public name of the application.\n"
        "- `maintenance_mode` — when true, clients should show a maintenance "
        "notice and pause new application workflows.\n"
        "- `evaluators_per_application` — number of evaluators assigned to each "
        "application.\n\n"
        "Requires authentication."
    ),
)
def get_system_settings(request):
    return SystemSettings.load()


@router.patch(
    "/settings",
    response=SettingsOut,
    tags=["Single types"],
    summary="Update system settings",
    operation_id="updateSystemSettings",
    description=(
        "Update one or more system settings. This is a partial update: omitted "
        "fields keep their current values.\n\n"
        "**Permissions**\n"
        "Requires the `api.change_systemsettings` Django permission. No staff "
        "status or group membership is required; assign the permission directly "
        "to a user or through a group.\n\n"
        "**Validation**\n"
        "- `site_name` must be between 1 and 100 characters.\n"
        "- `evaluators_per_application` must be at least 1.\n\n"
        "Returns the complete settings object after the update."
    ),
)
@csrf_exempt
def update_system_settings(request, payload: SettingsIn):
    if not request.auth.has_perm(PERM_CHANGE_SYSTEM_SETTINGS):
        raise HttpError(
            403, "You do not have permission to change system settings."
        )

    settings = SystemSettings.load()
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)

    try:
        settings.full_clean()
        settings.save()
    except ValidationError as error:
        _raise_validation_error(error)
    return settings
