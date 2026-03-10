from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, Field, validator


# ── Reusable light items ─────────────────────────────────────────────

class DashboardUserItem(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    role: str
    isAvailable: Optional[bool] = True

    class Config:
        from_attributes = True


class DashboardPlayerItem(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    position: str
    rating: Optional[int] = None
    shirtNumber: Optional[int] = None
    avatar: Optional[str] = Field(None, example="")
    teamId: int
    teamName: Optional[str] = None
    goalsCount: int = 0
    assistsCount: int = 0
    yellowCardsCount: int = 0
    redCardsCount: int = 0
    appearancesCount: int = 0

    @validator("avatar", pre=False, always=True)
    def decode_avatar_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    class Config:
        from_attributes = True


class DashboardTeamItem(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    logo: Optional[str] = Field(None, example="")
    playerCount: int = 0
    isDefault: Optional[bool] = False

    @validator("logo", pre=False, always=True)
    def decode_logo_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    class Config:
        from_attributes = True


class DashboardMatchItem(BaseModel):
    id: int
    team1Id: int
    team2Id: int
    team1Name: Optional[str] = None
    team2Name: Optional[str] = None
    team1Logo: Optional[str] = Field(None, example="")
    team2Logo: Optional[str] = Field(None, example="")
    location: Optional[str] = None
    timestamp: Optional[datetime] = None
    scoreTeam1: Optional[int] = None
    scoreTeam2: Optional[int] = None
    state: str
    leagueId: Optional[int] = None
    leagueName: Optional[str] = None
    leagueLogo: Optional[str] = Field(None, example="")
    round: Optional[int] = None

    @validator("team1Logo", "team2Logo", "leagueLogo", pre=False, always=True)
    def decode_logo_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    class Config:
        from_attributes = True


class DashboardGoalItem(BaseModel):
    id: int
    matchId: int
    playerId: Optional[int] = None
    playerName: Optional[str] = None
    assistPlayerId: Optional[int] = None
    assistPlayerName: Optional[str] = None
    teamId: int
    teamName: Optional[str] = None
    minute: Optional[int] = None

    class Config:
        from_attributes = True


class DashboardTournamentItem(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    formatType: Optional[str] = None
    groupCount: Optional[int] = None
    teamsPerGroup: Optional[int] = None
    hasKnockout: Optional[bool] = None

    class Config:
        from_attributes = True


class DashboardLeagueItem(BaseModel):
    id: int
    name: str
    logo: Optional[str] = Field(None, example="")
    season: Optional[str] = None
    relevanceOrder: Optional[int] = None
    tournamentId: int
    startDate: Optional[date] = None
    endDate: Optional[date] = None

    @validator("logo", pre=False, always=True)
    def decode_logo_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    class Config:
        from_attributes = True


class DashboardRankingItem(BaseModel):
    id: int
    teamId: int
    teamName: Optional[str] = None
    teamLogo: Optional[str] = Field(None, example="")
    leagueId: Optional[int] = None
    leagueName: Optional[str] = None
    leagueLogo: Optional[str] = Field(None, example="")
    points: int = 0
    gamesPlayed: int = 0
    gamesWon: int = 0
    gamesLost: int = 0
    gamesTied: int = 0
    goalsScored: int = 0
    goalsConceded: int = 0

    @validator("teamLogo", "leagueLogo", pre=False, always=True)
    def decode_logo_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    class Config:
        from_attributes = True


class DashboardTrainingItem(BaseModel):
    id: int
    timestamp: Optional[datetime] = None
    location: Optional[str] = None
    details: Optional[str] = None

    class Config:
        from_attributes = True


class DashboardAttendanceItem(BaseModel):
    id: int
    scope: str
    matchId: Optional[int] = None
    trainingSessionId: Optional[int] = None
    tournamentId: Optional[int] = None
    playerId: int
    playerName: Optional[str] = None
    teamId: int
    status: str
    recordedAt: Optional[datetime] = None

    class Config:
        from_attributes = True


class DashboardNotificationItem(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    userId: int
    type: str
    createdAt: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Stats overview ───────────────────────────────────────────────────

class DashboardStatsResponse(BaseModel):
    totalUsers: int = 0
    totalPlayers: int = 0
    totalTeams: int = 0
    totalMatches: int = 0
    totalGoals: int = 0
    totalTournaments: int = 0
    totalTrainingSessions: int = 0


# ── List wrappers ────────────────────────────────────────────────────

class DashboardListResponse(BaseModel):
    data: list
    total: int
