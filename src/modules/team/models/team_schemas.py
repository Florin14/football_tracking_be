from typing import List

from pydantic import Field

from project_helpers.schemas import BaseSchema, FilterSchema


class TeamAdd(BaseSchema):
    email: str = Field(..., max_length=40, example="cicada.cws@gmail.com")
    name: str = Field(..., max_length=50, example="Gal Attila")


class TeamItem(BaseSchema):
    id: int
    name: str
    role: str
    email: str


class TeamFilter(FilterSchema):
    sortBy: str = "name"


class TeamResponse(BaseSchema):
    id: int
    name: str
    role: str
    email: str


class TeamListResponse(BaseSchema):
    data: List[TeamItem] = []
