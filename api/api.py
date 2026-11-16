from ninja import NinjaAPI
from ninja.security import django_auth

from .features import auth_router, applications_router

# Session-id (cookie) auth: the `sessionid` cookie is resolved by Django's
# SessionMiddleware/AuthenticationMiddleware; unsafe methods require a CSRF token.
api = NinjaAPI(auth=django_auth)

# Register feature routers
api.add_router("/auth", auth_router, tags=["auth"])
api.add_router("/applications", applications_router, tags=["applications"])


@api.get("/health", auth=None)
def health_check(request):
    return {"status": "ok"}
