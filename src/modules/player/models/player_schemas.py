from typing import List

from pydantic import Field

from project_helpers.schemas import BaseSchema, FilterSchema


class PlayerAdd(BaseSchema):
    email: str = Field(..., max_length=40, example="cicada.cws@gmail.com")
    name: str = Field(..., max_length=50, example="Gal Attila")


class PlayerItem(BaseSchema):
    id: int
    name: str
    role: str
    email: str


class PlayerFilter(FilterSchema):
    sortBy: str = "name"


class PlayerResponse(BaseSchema):
    id: int
    name: str
    role: str
    email: str


class PlayerListResponse(BaseSchema):
    data: List[PlayerItem] = []
