from datetime import datetime
from typing import List, Optional

from pydantic import Field

from project_helpers.schemas import BaseSchema, FilterSchema


class AttendanceUpsert(BaseSchema):
    scope: str = Field("MATCH", example="MATCH")
    matchId: Optional[int] = Field(None, example=1)
    tournamentId: Optional[int] = Field(None, example=1)
    trainingSessionId: Optional[int] = Field(None, example=1)
    playerId: int = Field(..., example=1)
    teamId: Optional[int] = Field(None, example=1)
    status: str = Field(..., example="PRESENT")
    note: Optional[str] = Field(None, max_length=255, example="Arrived late due to traffic")


class AttendanceUpdate(BaseSchema):
    status: Optional[str] = Field(None, example="ABSENT")
    note: Optional[str] = Field(None, max_length=255)


class AttendanceResponse(BaseSchema):
    id: int
    scope: str
    matchId: Optional[int] = None
    trainingSessionId: Optional[int] = None
    playerId: int
    playerName: str
    teamId: int
    teamName: str
    status: str
    note: Optional[str] = None
    recordedAt: datetime
    leagueId: Optional[int] = Field(None, validation_alias="resolvedLeagueId")
    tournamentId: Optional[int] = Field(None, validation_alias="resolvedTournamentId")


class AttendanceListResponse(BaseSchema):
    data: List[AttendanceResponse] = []


class AttendanceTournamentGroupResponse(BaseSchema):
    tournamentId: Optional[int] = None
    items: List[AttendanceResponse] = []


class AttendancePlayerGroupResponse(BaseSchema):
    playerId: int
    playerName: str
    tournaments: List[AttendanceTournamentGroupResponse] = []


class AttendanceGroupedListResponse(BaseSchema):
    data: List[AttendancePlayerGroupResponse] = []


class AttendanceFilter(FilterSchema):
    scope: Optional[str] = None
    matchId: Optional[int] = None
    playerId: Optional[int] = None
    teamId: Optional[int] = None
    tournamentId: Optional[int] = None
    trainingSessionId: Optional[int] = None
    leagueId: Optional[int] = None
    tournamentId: Optional[int] = None
    status: Optional[str] = None
    sortBy: str = "recordedAt"
