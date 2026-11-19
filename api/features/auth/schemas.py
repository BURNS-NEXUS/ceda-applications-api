from ninja import Field, Schema


class LoginIn(Schema):
    email: str
    password: str


class RegisterIn(Schema):
    email: str = Field(..., format="email")
    password: str
    first_name: str
    last_name: str


class UserOut(Schema):
    id: str
    email: str
    first_name: str
    last_name: str


class UserPermissionsOut(Schema):
    user_id: str
    username: str
    is_superuser: bool
    permissions: list[str]
