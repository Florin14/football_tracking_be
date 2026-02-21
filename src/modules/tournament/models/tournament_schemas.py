from typing import Dict, List, Optional
from datetime import date, datetime

from pydantic import AliasChoices, Field, validator

from project_helpers.schemas import BaseSchema, FilterSchema, PaginationParams

class TeamItemLite(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    playerCount: Optional[int] = 0
    logo: Optional[str] = Field(None, example="")
    points: Optional[int] = 0
    goalsFor: Optional[int] = 0
    goalsAgainst: Optional[int] = 0
    wins: Optional[int] = 0
    draws: Optional[int] = 0
    losses: Optional[int] = 0

    @validator("logo", pre=False, always=True)
    def decode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value
from project_helpers.functions import process_and_convert_image_to_base64


class LeagueAdd(BaseSchema):
    name: str = Field(..., max_length=50, example="Premier League")
    description: Optional[str] = Field(None, max_length=200, example="League description")
    logo: Optional[bytes] = Field(None)
    startDate: Optional[date] = None
    endDate: Optional[date] = None
    season: Optional[str] = Field(None, max_length=9, example="2025-2026")
    relevanceOrder: Optional[int] = None

    @validator("logo", pre=False, always=True)
    def encode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return process_and_convert_image_to_base64(value, 316)
        return value


class LeagueUpdate(BaseSchema):
    logo: Optional[bytes] = Field(None)

    @validator("logo", pre=False, always=True)
    def encode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return process_and_convert_image_to_base64(value, 316)
        return value


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


class TournamentListParams(PaginationParams):
    search: Optional[str] = None
    excludeNullFormat: Optional[bool] = None


class LeagueListParams(PaginationParams):
    search: Optional[str] = None
    tournamentId: Optional[int] = Field(None, validation_alias=AliasChoices("tournamentId", "tournament_id"))


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


class LeaguesListResponse(BaseSchema):
    data: List[LeagueItem] = []


class LeagueDetail(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    logo: Optional[str] = Field(None, example="")
    season: Optional[str] = None
    relevanceOrder: Optional[int] = None
    tournamentId: Optional[int] = None

    @validator("logo", pre=False, always=True)
    def decode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value


class LeagueTeamsResponse(BaseSchema):
    league: LeagueDetail
    teams: List[TeamItemLite] = []


class LeagueTeamsAssignRequest(BaseSchema):
    teamIds: List[int] = []


class LeagueReorderItem(BaseSchema):
    leagueId: int
    relevanceOrder: Optional[int] = None


class LeagueReorderRequest(BaseSchema):
    leagueIds: Optional[List[int]] = None
    leagues: List[LeagueReorderItem] = Field(default_factory=list)


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


class TournamentGroupBulkItem(BaseSchema):
    name: str = Field(..., max_length=50, example="Group A")
    order: Optional[int] = Field(None, example=1)
    teamIds: List[int] = []


class TournamentGroupBulkCreateRequest(BaseSchema):
    groups: List[TournamentGroupBulkItem] = []
    replaceExisting: bool = False


class TournamentGroupCreateRequest(BaseSchema):
    name: Optional[str] = Field(None, max_length=50, example="Group A")
    order: Optional[int] = Field(None, example=1)
    teamIds: List[int] = []
    groups: List[TournamentGroupBulkItem] = []
    replaceExisting: bool = False


class TournamentGroupTeamsUpdate(BaseSchema):
    teamIds: List[int] = []


class TournamentGroupItem(BaseSchema):
    id: int
    name: str
    order: Optional[int] = None
    teams: List[TeamItemLite] = []


class TournamentGroupsAutoAssignRequest(BaseSchema):
    groupCount: Optional[int] = None
    teamsPerGroup: Optional[int] = None
    shuffleTeams: bool = True
    replaceExisting: bool = False


class TournamentGroupScheduleRequest(BaseSchema):
    startTimestamp: datetime
    intervalMinutes: int = Field(90, ge=1)
    randomize: bool = True
    avoidConsecutive: bool = True
    replaceExisting: bool = False
    leagueId: Optional[int] = None


class TournamentGroupScheduleSimpleRequest(BaseSchema):
    mode: str = Field("round-robin", example="round-robin")
    avoidConsecutive: bool = True
    startTimestamp: Optional[datetime] = None
    intervalMinutes: int = Field(90, ge=1)
    randomize: bool = True
    replaceExisting: bool = False
    leagueId: Optional[int] = None


class TournamentGroupMatchItem(BaseSchema):
    id: int
    groupId: int
    matchId: int
    round: Optional[int] = None
    order: Optional[int] = None
    team1Id: int
    team2Id: int
    scoreTeam1: Optional[int] = None
    scoreTeam2: Optional[int] = None
    state: str
    timestamp: datetime


class TournamentGroupMatchesResponse(BaseSchema):
    groups: List[TournamentGroupItem] = []
    matches: List[TournamentGroupMatchItem] = []


class TournamentGroupStandingsItem(BaseSchema):
    groupId: int
    groupName: str
    teams: List[TeamItemLite] = []


class TournamentGroupStandingsResponse(BaseSchema):
    groups: List[TournamentGroupStandingsItem] = []


class TournamentKnockoutMatchAdd(BaseSchema):
    matchId: int = Field(..., example=1)
    round: Optional[str] = Field(None, max_length=50, example="Quarterfinal")
    order: Optional[int] = Field(None, example=1)


class TournamentKnockoutMatchCreate(BaseSchema):
    team1Id: int
    team2Id: int
    round: Optional[str] = Field(None, max_length=50, example="Quarterfinal")
    order: Optional[int] = Field(None, example=1)
    timestamp: datetime
    location: Optional[str] = None


class TournamentKnockoutBulkCreateRequest(BaseSchema):
    matches: List[TournamentKnockoutMatchCreate] = []
    replaceExisting: bool = False


class TournamentKnockoutAutoRequest(BaseSchema):
    qualifiersPerGroup: int = Field(..., ge=1, example=2)
    round: Optional[str] = Field(None, max_length=50, example="Quarterfinal")
    startTimestamp: datetime
    intervalMinutes: int = Field(90, ge=1)
    pairingStrategy: str = Field("cross", example="cross")
    replaceExisting: bool = False
    leagueId: Optional[int] = None


class TournamentKnockoutGenerateRequest(BaseSchema):
    startTimestamp: Optional[datetime] = None
    intervalMinutes: int = Field(90, ge=1)
    replaceExisting: bool = True
    leagueId: Optional[int] = None


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


class LeagueStandingsResponse(BaseSchema):
    league: LeagueDetail
    tournamentId: int
    formatType: Optional[str] = None
    groupCount: Optional[int] = None
    teamsPerGroup: Optional[int] = None
    hasKnockout: Optional[bool] = None
    groups: List[TournamentGroupStandingsItem] = []
    knockoutMatches: List[TournamentKnockoutMatchItem] = []


class TournamentStructureResponse(BaseSchema):
    tournamentId: int
    formatType: Optional[str] = None
    groupCount: Optional[int] = None
    teamsPerGroup: Optional[int] = None
    hasKnockout: Optional[bool] = None
    groups: List[TournamentGroupItem] = []
    knockoutMatches: List[TournamentKnockoutMatchItem] = []


class KnockoutManualPair(BaseSchema):
    home: str
    away: str


class TournamentKnockoutConfig(BaseSchema):
    qualifiersPerGroup: Optional[int] = None
    pairingMode: Optional[str] = None
    manualPairs: List[KnockoutManualPair] = []
    pairingConfig: Optional[Dict[str, str]] = None
    manualPairsByPhase: Optional[Dict[str, List[KnockoutManualPair]]] = None


class TournamentPlanResponse(BaseSchema):
    tournamentId: int
    formatType: Optional[str] = None
    groupCount: Optional[int] = None
    teamsPerGroup: Optional[int] = None
    hasKnockout: Optional[bool] = None
    groups: List[TournamentGroupItem] = []
    groupMatches: List[TournamentGroupMatchItem] = []
    knockoutConfig: Optional[TournamentKnockoutConfig] = None
    knockoutMatches: List[TournamentKnockoutMatchItem] = []
