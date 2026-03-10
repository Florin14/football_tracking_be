from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel


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
    teamId: int
    teamName: Optional[str] = None
    goalsCount: int = 0
    assistsCount: int = 0
    yellowCardsCount: int = 0
    redCardsCount: int = 0
    appearancesCount: int = 0

    class Config:
        from_attributes = True


class DashboardTeamItem(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    playerCount: int = 0
    isDefault: Optional[bool] = False

    class Config:
        from_attributes = True


class DashboardMatchItem(BaseModel):
    id: int
    team1Id: int
    team2Id: int
    team1Name: Optional[str] = None
    team2Name: Optional[str] = None
    location: Optional[str] = None
    timestamp: Optional[datetime] = None
    scoreTeam1: Optional[int] = None
    scoreTeam2: Optional[int] = None
    state: str
    leagueName: Optional[str] = None
    round: Optional[int] = None

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
    season: Optional[str] = None
    relevanceOrder: Optional[int] = None
    tournamentId: int
    startDate: Optional[date] = None
    endDate: Optional[date] = None

    class Config:
        from_attributes = True


class DashboardRankingItem(BaseModel):
    id: int
    teamId: int
    teamName: Optional[str] = None
    leagueId: Optional[int] = None
    points: int = 0
    gamesPlayed: int = 0
    gamesWon: int = 0
    gamesLost: int = 0
    gamesTied: int = 0
    goalsScored: int = 0
    goalsConceded: int = 0

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
