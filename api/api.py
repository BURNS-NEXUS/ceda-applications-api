from ninja import NinjaAPI
from ninja.security import django_auth

from .features import (
    applications_router,
    audit_logs_router,
    auth_router,
    clarifications_router,
    corporate_details_router,
    financial_details_router,
    personal_details_router,
    references_router,
)

# Session-id (cookie) auth: the `sessionid` cookie is resolved by Django's
# SessionMiddleware/AuthenticationMiddleware; unsafe methods require a CSRF token.
api = NinjaAPI(auth=django_auth)

# Register feature routers
api.add_router("/auth", auth_router, tags=["Auth"])
api.add_router("/applications", applications_router, tags=["Applications"])
api.add_router("/clarifications", clarifications_router, tags=["Clarifications"])
api.add_router("/audit-logs", audit_logs_router, tags=["Audit logs"])
api.add_router("", personal_details_router)
api.add_router("", corporate_details_router)
api.add_router("", references_router)
api.add_router("", financial_details_router)


@api.get("/health", auth=None, tags=["Health"])
def health_check(request):
    return {"status": "ok"}
