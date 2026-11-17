from ninja import Query, Router
from ninja.errors import HttpError

from .models import Clarification
from .schemas import ClarificationFilters, ClarificationListOut

router = Router()


@router.get("/", response=ClarificationListOut)
def list_clarifications(request, filters: Query[ClarificationFilters]):
    if not request.auth.groups.filter(name="admin").exists():
        raise HttpError(403, "You do not have permission to view audit logs")
    logs = Clarification.objects.all()
    total = logs.count()
    stop = filters.skip + filters.take if filters.take is not None else None
    return {"total": total, "data": logs[filters.skip : stop]}
