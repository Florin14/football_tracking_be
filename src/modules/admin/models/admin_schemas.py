from typing import List, Optional

from pydantic import Field

from constants.platform_roles import PlatformRoles
from project_helpers.schemas import BaseSchema, FilterSchema


class AdminAdd(BaseSchema):
    email: str = Field(..., max_length=40, example="email@gmail.com")
    name: str = Field(..., max_length=50, example="Gal Attila")
    role: PlatformRoles = Field(..., example=PlatformRoles.ADMIN)
    password: str

class AdminItem(BaseSchema):
    id: int
    name: str
    role: str
    email: str


class AdminFilter(FilterSchema):
    sortBy: str = "companyName"


class AdminResponse(BaseSchema):
    id: int
    name: str
    role: str
    email: str


class AdminListResponse(BaseSchema):
    data: List[AdminItem] = []