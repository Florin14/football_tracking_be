from typing import List, Optional
from datetime import datetime

from pydantic import Field

from project_helpers.schemas import BaseSchema, FilterSchema


class GoalResponse(BaseSchema):
    id: int
    matchId: int
    playerId: Optional[int] = None
    playerName: str
    assistPlayerId: Optional[int] = None
    assistPlayerName: Optional[str] = None
    teamId: int
    teamName: str
    minute: Optional[int] = None
    timestamp: datetime
    description: Optional[str] = None


class GoalListResponse(BaseSchema):
    data: List[GoalResponse] = []


class GoalFilter(FilterSchema):
    matchId: Optional[int] = None
    playerId: Optional[int] = None
    teamId: Optional[int] = None
    sortBy: str = "timestamp"
