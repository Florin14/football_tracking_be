from typing import List, Optional

from pydantic import Field, validator

from project_helpers.schemas import BaseSchema, FilterSchema


class RankingAdd(BaseSchema):
    name: str = Field(..., max_length=50, example="Base Camp")
    description: Optional[str] = Field(None, max_length=200, example="Tournament")


class RankingUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=200)


class AddTeamToRanking(BaseSchema):
    playerId: int = Field(..., example=1)


class TeamItem(BaseSchema):
    id: int
    name: str
    isDefault: bool
    logo: Optional[str] = Field(None, example="")

    @validator("logo", pre=False, always=True)
    def decode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value


class RankingItem(BaseSchema):
    id: int
    team: TeamItem
    points: int
    gamesPlayed: int
    goalsScored: int
    goalsConceded: int
    gamesWon: int
    gamesTied: int
    gamesLost: int
    form: str


class RankingFilter(FilterSchema):
    sortBy: str = "name"


class RankingResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None


class RankingListResponse(BaseSchema):
    data: List[RankingItem] = []
