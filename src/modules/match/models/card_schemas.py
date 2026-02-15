from typing import Optional
from datetime import datetime

from pydantic import Field

from project_helpers.schemas import BaseSchema


class CardAdd(BaseSchema):
    playerId: int = Field(..., example=1)
    teamId: int = Field(..., example=1)
    cardType: str = Field(..., example="YELLOW", description="YELLOW or RED")
    minute: Optional[int] = Field(None, example=45)


class CardResponse(BaseSchema):
    id: int
    matchId: int
    playerId: int
    teamId: int
    cardType: str
    minute: Optional[int] = None
    timestamp: datetime
