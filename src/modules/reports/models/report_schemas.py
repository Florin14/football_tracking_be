from datetime import date, datetime
from typing import List, Optional

from project_helpers.schemas import BaseSchema


class ReportTeamItem(BaseSchema):
    id: int
    name: str


class PerformanceSummary(BaseSchema):
    matchesPlayed: int
    wins: int
    draws: int
    losses: int
    goalsFor: int
    goalsAgainst: int
    goalDiff: int
    cleanSheets: int
    avgGoalsFor: float
    avgGoalsAgainst: float
    biggestWin: Optional[str] = None
    biggestLoss: Optional[str] = None
    formLast5: List[str] = []


class PerformanceTrendItem(BaseSchema):
    label: str
    goalsFor: int
    goalsAgainst: int


class PerformancePositionStat(BaseSchema):
    position: str
    goals: int
    players: int


class PerformancePlayerStat(BaseSchema):
    playerId: int
    name: str
    goals: int


class PerformanceAssistStat(BaseSchema):
    playerId: int
    name: str
    assists: int


class PerformanceMonthlyWins(BaseSchema):
    month: str
    label: str
    wins: int


class PerformanceReportResponse(BaseSchema):
    team: ReportTeamItem
    summary: PerformanceSummary
    trend: List[PerformanceTrendItem] = []
    positionStats: List[PerformancePositionStat] = []
    topScorers: List[PerformancePlayerStat] = []
    topAssists: List[PerformanceAssistStat] = []
    monthlyWins: List[PerformanceMonthlyWins] = []
