from ninja import Query, Router
from ninja.errors import HttpError
from django.db.models.functions import Lower

from .models import AuditLog
from .schemas import AuditLogFilters, AuditLogListOut

router = Router()

# Adjudicators do not get the global audit-log permission. They may read the
# decision-related slice of the log so their portal can show a real history
# without exposing unrelated platform activity.
ADJUDICATOR_AUDIT_RESOURCES = ("application", "applicationadjudication")


def _serialize(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "actor_id": log.actor_id,
        "actor_username": log.actor.username if log.actor else None,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "details": log.details,
        "created_at": log.created_at,
    }


@router.get("/", response=AuditLogListOut)
def list_audit_logs(request, filters: Query[AuditLogFilters]):
    can_view_all = request.auth.has_perm("api.view_auditlog") or (
        request.auth.groups.filter(name="admin").exists()
    )
    can_adjudicate = request.auth.has_perm("scoring.adjudicate_application")
    if not (can_view_all or can_adjudicate):
        raise HttpError(403, "You do not have permission to view audit logs")

    logs = AuditLog.objects.select_related("actor").all()
    if not can_view_all:
        logs = logs.annotate(
            resource_type_lower=Lower("resource_type")
        ).filter(resource_type_lower__in=ADJUDICATOR_AUDIT_RESOURCES)

    total = logs.count()
    stop = filters.skip + filters.take if filters.take is not None else None
    return {
        "total": total,
        "data": [_serialize(log) for log in logs[filters.skip : stop]],
    }
