from typing import List, Optional

from pydantic import Field

from project_helpers.schemas import BaseSchema, FilterSchema


class TeamAdd(BaseSchema):
    name: str = Field(..., max_length=50, example="Nordic Lions")
    description: Optional[str] = Field(None, max_length=200, example="Professional football team")


class TeamUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=200)


class AddPlayerToTeam(BaseSchema):
    playerId: int = Field(..., example=1)


class TeamItem(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    playerCount: Optional[int] = 0


class TeamFilter(FilterSchema):
    sortBy: str = "name"


class TeamResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    players: Optional[List[dict]] = []


class TeamListResponse(BaseSchema):
    data: List[TeamItem] = []
