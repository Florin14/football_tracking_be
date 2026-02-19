from datetime import datetime
from typing import Optional, List

from pydantic import AliasChoices, Field, validator

from project_helpers.schemas import BaseSchema, FilterSchema, PaginationParams
from modules.match.models.goal_schemas import GoalResponse


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
    friendly: bool = Field(False, example=False)
    round: Optional[int] = Field(None, ge=1, example=1)
    location: Optional[str] = Field(None, min_length=1, example="Stadium Arena")
    timestamp: datetime = Field(..., example="2024-12-25T15:00:00")
    youtubeUrl: Optional[str] = Field(None, example="https://www.youtube.com/watch?v=dQw4w9WgXcQ")

class GoalAdd(BaseSchema):
    playerId: int = Field(..., example=1)
    assistPlayerId: Optional[int] = Field(None, example=2)
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
    round: Optional[int] = Field(None, ge=1)
    youtubeUrl: Optional[str] = None


class ScoreUpdate(BaseSchema):
    goals: List[GoalAdd] = Field(..., description="List of goals scored by your team")


class MatchItem(BaseSchema):
    id: int
    team1Id: int
    team2Id: int
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
    round: Optional[int] = None
    youtubeUrl: Optional[str] = None

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
    goals: Optional[List[GoalResponse]] = []
    round: Optional[int] = None
    youtubeUrl: Optional[str] = None


class MatchFilter(FilterSchema):
    teamId: Optional[int] = None
    state: Optional[str] = None
    sortBy: str = "timestamp"


class MatchListParams(PaginationParams):
    teamId: Optional[int] = Field(None, validation_alias=AliasChoices("teamId", "team_id"))
    state: Optional[str] = None


class MatchListResponse(BaseSchema):
    data: List[MatchItem] = []


class ObjectItem(BaseSchema):
    id: int
    name: str

class TeamOut(BaseSchema):
    id: int
    name: str
    isDefault: bool

    class Config:
        from_attributes = True 
        
class LeagueOut(BaseSchema):
    id: int
    name: str
    season: str
    teams: List[TeamOut] = []

    class Config:
        from_attributes = True

class MatchResourcesResponse(BaseSchema):
    leagues: List[LeagueOut]
    allTeams: List[TeamOut] = []
