from .applications.router import router as applications_router
from .audit_logs.router import router as audit_logs_router
from .auth.me_router import router as auth_me_router
from .auth.router import router as auth_router
from .clarifications.router import router as clarifications_router
from .corporate_details.router import router as corporate_details_router
from .documents.router import router as documents_router
from .financial_details.router import router as financial_details_router
from .personal_details.router import router as personal_details_router
from .references.router import router as references_router

__all__ = [
    "applications_router",
    "audit_logs_router",
    "auth_me_router",
    "auth_router",
    "clarifications_router",
    "corporate_details_router",
    "documents_router",
    "financial_details_router",
    "personal_details_router",
    "references_router",
]
