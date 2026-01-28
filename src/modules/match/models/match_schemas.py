from datetime import datetime
from typing import Optional, List

from pydantic import Field, validator

from project_helpers.schemas import BaseSchema, FilterSchema


class LeagueItemLite(BaseSchema):
    id: int
    name: str
    logo: Optional[str] = Field(None, example="")
    relevanceOrder: Optional[int] = None
    tournamentId: Optional[int] = None

    @validator("logo", pre=False, always=True)
    def decode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value


class MatchAdd(BaseSchema):
    team1Id: int = Field(..., example=1)
    team2Id: int = Field(..., example=2)
    leagueId: Optional[int] = Field(None, example=1)
    location: Optional[str] = Field(None, min_length=1, example="Stadium Arena")
    timestamp: datetime = Field(..., example="2024-12-25T15:00:00")

class GoalAdd(BaseSchema):
    playerId: int = Field(..., example=1)
    teamId: int = Field(..., example=1)
    minute: Optional[int] = Field(None, example=45)
    description: Optional[str] = Field(None, max_length=200, example="Header from corner kick")

class MatchUpdate(BaseSchema):
    location: Optional[str] = Field(None, min_length=1)
    timestamp: Optional[datetime] = None
    scoreTeam1: Optional[int] = None
    scoreTeam2: Optional[int] = None
    state: Optional[str] = None
    goals: Optional[List[GoalAdd]] = None


class ScoreUpdate(BaseSchema):
    goals: List[GoalAdd] = Field(..., description="List of goals scored by your team")


class MatchItem(BaseSchema):
    id: int
    team1Name: str
    team2Name: str
    team1Logo: Optional[str] = Field(None, example="")
    team2Logo: Optional[str] = Field(None, example="")
    leagueId: Optional[int] = None
    leagueName: Optional[str] = None
    leagueLogo: Optional[str] = Field(None, example="")
    location: Optional[str] = None
    timestamp: datetime
    scoreTeam1: Optional[int] = None
    scoreTeam2: Optional[int] = None
    state: str

    @validator("team1Logo", "team2Logo", "leagueLogo", pre=False, always=True)
    def decode_logo_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

class TeamItem(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    isDefault: bool
    playerCount: Optional[int] = 0
    logo: Optional[str] = Field(None, example="")

    @validator("logo", pre=False, always=True)
    def decode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

class MatchResponse(BaseSchema):
    id: int
    team1: TeamItem
    team2: TeamItem
    league: Optional[LeagueItemLite] = None
    location: Optional[str] = None
    timestamp: datetime
    scoreTeam1: Optional[int] = None
    scoreTeam2: Optional[int] = None
    state: str
    goals: Optional[List[dict]] = []


class MatchFilter(FilterSchema):
    teamId: Optional[int] = None
    state: Optional[str] = None
    sortBy: str = "timestamp"


class MatchListResponse(BaseSchema):
    data: List[MatchItem] = []


class ObjectItem(BaseSchema):
    id: int
    name: str

class MatchResourceTeamItem(BaseSchema):
    id: int
    name: str
    isDefault: bool
    location: Optional[str] = None

class MatchResourcesResponse(BaseSchema):
    teams: List[MatchResourceTeamItem] = []
    leagues: List[ObjectItem] = []
