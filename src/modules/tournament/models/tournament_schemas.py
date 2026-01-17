from typing import List, Optional

from pydantic import Field

from project_helpers.schemas import BaseSchema, FilterSchema


class TournamentAdd(BaseSchema):
    name: str = Field(..., max_length=50, example="Base Camp")
    description: Optional[str] = Field(None, max_length=200, example="Tournament")


class TournamentUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=200)


class AddTeamToTournament(BaseSchema):
    teamId: int = Field(..., example=1)


class TournamentItem(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    playerCount: Optional[int] = 0


class TournamentFilter(FilterSchema):
    sortBy: str = "name"


class TournamentResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None


class TournamentListResponse(BaseSchema):
    data: List[TournamentItem] = []
