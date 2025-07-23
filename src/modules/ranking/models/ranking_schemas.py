from typing import List, Optional

from pydantic import Field

from project_helpers.schemas import BaseSchema, FilterSchema


class RankingAdd(BaseSchema):
    name: str = Field(..., max_length=50, example="Nordic Lions")
    description: Optional[str] = Field(None, max_length=200, example="Tournament")


class RankingUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=200)


class AddTeamToRanking(BaseSchema):
    playerId: int = Field(..., example=1)


class RankingItem(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    playerCount: Optional[int] = 0


class RankingFilter(FilterSchema):
    sortBy: str = "name"


class RankingResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None


class RankingListResponse(BaseSchema):
    data: List[RankingItem] = []
