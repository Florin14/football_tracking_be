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
    hasDefaultPassword: bool
    isAvailable: bool
    nrOfInvalidatedNaturalPersons: Optional[int] = Field(
        default=None, example=0, description="Number of invalidated accounts"
    )
    nrOfInvalidatedLegalEntities: Optional[int] = Field(
        default=None, example=0, description="Number of invalidated accounts"
    )
    communications: Optional[int] = Field(default=None, example=0, description="Number of submissions")
