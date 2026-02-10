from typing import Optional

from pydantic import Field

from constants.platform_roles import PlatformRoles
from project_helpers.schemas import BaseSchema


class LoginBody(BaseSchema):
    email: str = "email@gmail.com"
    password: str = "password1234."


class LoginResponse(BaseSchema):
    id: int
    name: str
    role: PlatformRoles
    isAvailable: bool
    accessToken: Optional[str] = None
    refreshToken: Optional[str] = None


class RefreshTokenResponse(BaseSchema):
    message: Optional[str] = Field("Process was succesful", example="Process was succesful")
    accessToken: Optional[str] = None
    refreshToken: Optional[str] = None
