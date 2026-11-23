from ninja import NinjaAPI
from ninja.security import django_auth

from .features.absentees.router import router as absentees_router
from .features.applications.programmes import router as programmes_router
from .features.applications.router import router as applications_router
from .features.audit_logs.router import router as audit_logs_router
from .features.auth.me_router import router as auth_me_router
from .features.auth.router import router as auth_router
from .features.clarifications.router import router as clarifications_router
from .features.corporate_details.router import router as corporate_details_router
from .features.documents.router import router as documents_router
from .features.financial_details.router import router as financial_details_router
from .features.personal_details.router import router as personal_details_router
from .features.references.router import router as references_router
from .features.single_types.router import router as single_types_router
from .features.tasks.router import router as tasks_router
from .features.scoring.router import router as scoring_router
from .features.reporting.router import router as reporting_router

# Session-id (cookie) auth: the `sessionid` cookie is resolved by Django's
# SessionMiddleware/AuthenticationMiddleware; unsafe methods require a CSRF token.
api = NinjaAPI(auth=django_auth)

# Register feature routers
api.add_router("/programmes", programmes_router, tags=["Programme calls"])
api.add_router("/auth", auth_router, tags=["Auth"])
api.add_router("/me", auth_me_router, tags=["Auth"])
api.add_router("/applications", applications_router, tags=["Applications"])
api.add_router("", absentees_router, tags=["Absentees"])
api.add_router("/clarifications", clarifications_router, tags=["Clarifications"])
api.add_router("/audit-logs", audit_logs_router, tags=["Audit logs"])
api.add_router("", documents_router)
api.add_router("", personal_details_router)
api.add_router("", corporate_details_router)
api.add_router("", references_router)
api.add_router("", financial_details_router)
api.add_router("", single_types_router)
api.add_router("", scoring_router, tags=["Scoring"])
api.add_router("", reporting_router, tags=["Reporting"])
api.add_router("/tasks", tasks_router, tags=["Tasks"])


@api.get("/health", auth=None, tags=["Health"])
def health_check(request):
    return {"status": "ok"}
