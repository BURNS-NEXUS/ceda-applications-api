from typing import Optional

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


class UserPatchIn(Schema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = Field(None, format="email")


class UserPermissionsOut(Schema):
    user_id: str
    username: str
    is_superuser: bool
    permissions: list[str]
