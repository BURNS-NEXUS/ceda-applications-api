from ninja import Query, Router
from ninja.errors import HttpError

from .models import AuditLog
from .schemas import AuditLogFilters, AuditLogListOut

router = Router()


@router.get("/", response=AuditLogListOut)
def list_audit_logs(request, filters: Query[AuditLogFilters]):
    if not request.auth.has_perm("api.view_auditlog") and not request.auth.groups.filter(name="admin").exists():
        raise HttpError(403, "You do not have permission to view audit logs")
    logs = AuditLog.objects.all()
    total = logs.count()
    stop = filters.skip + filters.take if filters.take is not None else None
    return {"total": total, "data": logs[filters.skip : stop]}
