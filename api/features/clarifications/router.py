from ninja import Query, Router
from ninja.errors import HttpError

from .models import Clarification
from .schemas import ClarificationFilters, ClarificationListOut

router = Router()


@router.get("/", response=ClarificationListOut)
def list_clarifications(request, filters: Query[ClarificationFilters]):
    logs = Clarification.objects.order_by("-created_at", "-id")
    if not request.auth.has_perm("api.can_view_all_applications") and not request.auth.groups.filter(name="admin").exists():
        logs = logs.filter(application__owner=request.auth)
    if filters.application_id is not None:
        logs = logs.filter(application_id=filters.application_id)
    if filters.version is not None:
        logs = logs.filter(version=filters.version)
    total = logs.count()
    stop = filters.skip + filters.take if filters.take is not None else None
    return {"total": total, "data": logs[filters.skip : stop]}
