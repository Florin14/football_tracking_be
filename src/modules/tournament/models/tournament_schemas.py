from typing import List, Optional
from datetime import date, datetime

from pydantic import Field

from project_helpers.schemas import BaseSchema, FilterSchema
from modules.team.models import TeamItem


class LeagueAdd(BaseSchema):
    name: str = Field(..., max_length=50, example="Premier League")
    description: Optional[str] = Field(None, max_length=200, example="League description")
    startDate: Optional[date] = None
    endDate: Optional[date] = None
    season: Optional[str] = Field(None, max_length=9, example="2025-2026")
    relevanceOrder: Optional[int] = None


class TournamentAdd(BaseSchema):
    name: str = Field(..., max_length=50, example="Base Camp")
    description: Optional[str] = Field(None, max_length=200, example="Tournament")
    formatType: Optional[str] = Field(None, max_length=30, example="groups_only")
    groupCount: Optional[int] = Field(None, example=4)
    teamsPerGroup: Optional[int] = Field(None, example=4)
    hasKnockout: Optional[bool] = Field(None, example=True)
    leagues: Optional[List[LeagueAdd]] = None


class TournamentUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    formatType: Optional[str] = Field(None, max_length=30)
    groupCount: Optional[int] = None
    teamsPerGroup: Optional[int] = None
    hasKnockout: Optional[bool] = None


class AddTeamToTournament(BaseSchema):
    teamId: int = Field(..., example=1)


class TournamentItem(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    formatType: Optional[str] = None
    groupCount: Optional[int] = None
    teamsPerGroup: Optional[int] = None
    hasKnockout: Optional[bool] = None


class TournamentFilter(FilterSchema):
    sortBy: str = "name"


class TournamentResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    formatType: Optional[str] = None
    groupCount: Optional[int] = None
    teamsPerGroup: Optional[int] = None
    hasKnockout: Optional[bool] = None


class TournamentListResponse(BaseSchema):
    data: List[TournamentItem] = []



class LeagueItem(BaseSchema):
    id: int
    name: str
    relevanceOrder: Optional[int] = None
    tournamentId: Optional[int] = None


class LeaguesListResponse(BaseSchema):
    data: List[LeagueItem] = []


class LeagueDetail(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    season: Optional[str] = None
    relevanceOrder: Optional[int] = None
    tournamentId: Optional[int] = None


class LeagueTeamsResponse(BaseSchema):
    league: LeagueDetail
    teams: List[TeamItem] = []


class LeagueTeamsAssignRequest(BaseSchema):
    teamIds: List[int] = []


class LeagueReorderRequest(BaseSchema):
    leagueIds: List[int] = []


class TournamentResourceItem(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    formatType: Optional[str] = None
    groupCount: Optional[int] = None
    teamsPerGroup: Optional[int] = None
    hasKnockout: Optional[bool] = None
    leagues: List[LeagueItem] = []


class TournamentResourcesResponse(BaseSchema):
    tournaments: List[TournamentResourceItem] = []


class TournamentGroupAdd(BaseSchema):
    name: str = Field(..., max_length=50, example="Group A")
    order: Optional[int] = Field(None, example=1)
    teamIds: List[int] = []


class TournamentGroupTeamsUpdate(BaseSchema):
    teamIds: List[int] = []


class TournamentGroupItem(BaseSchema):
    id: int
    name: str
    order: Optional[int] = None
    teams: List[TeamItem] = []


class TournamentKnockoutMatchAdd(BaseSchema):
    matchId: int = Field(..., example=1)
    round: Optional[str] = Field(None, max_length=50, example="Quarterfinal")
    order: Optional[int] = Field(None, example=1)


class TournamentKnockoutMatchItem(BaseSchema):
    id: int
    matchId: int
    round: Optional[str] = None
    order: Optional[int] = None
    team1Id: int
    team2Id: int
    scoreTeam1: Optional[int] = None
    scoreTeam2: Optional[int] = None
    state: str
    timestamp: datetime


class TournamentStructureResponse(BaseSchema):
    tournamentId: int
    formatType: Optional[str] = None
    groupCount: Optional[int] = None
    teamsPerGroup: Optional[int] = None
    hasKnockout: Optional[bool] = None
    groups: List[TournamentGroupItem] = []
    knockoutMatches: List[TournamentKnockoutMatchItem] = []
