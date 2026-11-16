from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.middleware.csrf import get_token
from ninja import Router
from ninja.errors import HttpError

from .helpers import check_is_email
from .schemas import LoginIn, RegisterIn, UserOut

router = Router()


@router.get("/csrf", auth=None)
def csrf(request):
    """Sets the csrftoken cookie; clients send it back in the X-CSRFToken header."""
    return {"csrfToken": get_token(request)}


@router.post("/register", auth=None, response={201: UserOut})
def register(request, payload: RegisterIn):
    User = get_user_model()
    if not check_is_email(payload.email):
        raise HttpError(422, "Invalid email format")
    if User.objects.filter(username__iexact=payload.email).exists():
        raise HttpError(409, "Username already taken")
    try:
        validate_password(payload.password, User(username=payload.email))
    except ValidationError as e:
        raise HttpError(422, " ".join(e.messages))
    user = User.objects.create_user(
        username=payload.email,
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        is_active=True,
    )
    group, _ = Group.objects.get_or_create(name="customer")
    user.groups.add(group)
    login(request, user)
    return 201, user


@router.post("/login", auth=None, response=UserOut)
def login_view(request, payload: LoginIn):
    user = authenticate(request, username=payload.email, password=payload.password)
    if user is None:
        raise HttpError(401, "Invalid credentials")
    login(request, user)  # creates the session and sets the sessionid cookie
    return user


@router.post("/logout")
def logout_view(request):
    logout(request)  # flushes the session and deletes the cookie
    return {"success": True}


@router.get("/me", response=UserOut)
def get_current_user(request):
    return request.auth
