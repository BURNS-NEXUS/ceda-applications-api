from .auth.router import router as auth_router
from .applications.router import router as applications_router

__all__ = ["auth_router", "applications_router"]
