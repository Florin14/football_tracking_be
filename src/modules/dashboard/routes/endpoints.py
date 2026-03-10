from typing import Optional

from fastapi import Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.dashboard.dependencies import ApiKeyRequired
from modules.dashboard.schemas.dashboard_schemas import (
    DashboardAttendanceItem,
    DashboardGoalItem,
    DashboardLeagueItem,
    DashboardMatchItem,
    DashboardNotificationItem,
    DashboardPlayerItem,
    DashboardRankingItem,
    DashboardStatsResponse,
    DashboardTeamItem,
    DashboardTournamentItem,
    DashboardTrainingItem,
    DashboardUserItem,
)
from modules.attendance.models.attendance_model import AttendanceModel
from modules.match.models.goal_model import GoalModel
from modules.match.models.match_model import MatchModel
from modules.notifications.models.notifications_model import NotificationModel
from modules.player.models.player_model import PlayerModel
from modules.ranking.models.ranking_model import RankingModel
from modules.team.models.team_model import TeamModel
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.tournament_model import TournamentModel
from modules.training.models.training_session_model import TrainingSessionModel
from modules.user.models.user_model import UserModel

from .router import router

api_key = Depends(ApiKeyRequired())


# ── Stats overview ───────────────────────────────────────────────────

@router.get("/stats", response_model=DashboardStatsResponse, dependencies=[api_key])
def get_stats(db: Session = Depends(get_db)):
    return DashboardStatsResponse(
        totalUsers=db.query(func.count(UserModel.id)).filter(UserModel.isDeleted.is_(False)).scalar() or 0,
        totalPlayers=db.query(func.count(PlayerModel.id)).scalar() or 0,
        totalTeams=db.query(func.count(TeamModel.id)).scalar() or 0,
        totalMatches=db.query(func.count(MatchModel.id)).scalar() or 0,
        totalGoals=db.query(func.count(GoalModel.id)).scalar() or 0,
        totalTournaments=db.query(func.count(TournamentModel.id)).scalar() or 0,
        totalTrainingSessions=db.query(func.count(TrainingSessionModel.id)).scalar() or 0,
    )


# ── Users ────────────────────────────────────────────────────────────

@router.get("/users", response_model=list[DashboardUserItem], dependencies=[api_key])
def get_users(
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(UserModel).filter(UserModel.isDeleted.is_(False))
    if search:
        q = q.filter(UserModel.name.ilike(f"%{search}%"))
    users = q.order_by(UserModel.name).offset(offset).limit(limit).all()
    return [
        DashboardUserItem(
            id=u.id, name=u.name, email=u.email,
            role=str(u.role), isAvailable=u.isAvailable,
        )
        for u in users
    ]


# ── Players ──────────────────────────────────────────────────────────

@router.get("/players", response_model=list[DashboardPlayerItem], dependencies=[api_key])
def get_players(
    teamId: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(PlayerModel).options(joinedload(PlayerModel.team))
    if teamId:
        q = q.filter(PlayerModel.teamId == teamId)
    if search:
        q = q.filter(PlayerModel.name.ilike(f"%{search}%"))
    players = q.order_by(PlayerModel.name).offset(offset).limit(limit).all()
    return [
        DashboardPlayerItem(
            id=p.id, name=p.name, email=p.email,
            position=str(p.position), rating=p.rating,
            shirtNumber=p.shirtNumber, teamId=p.teamId,
            teamName=p.team.name if p.team else None,
            goalsCount=p.goalsCount, assistsCount=p.assistsCount,
            yellowCardsCount=p.yellowCardsCount, redCardsCount=p.redCardsCount,
            appearancesCount=p.appearancesCount,
        )
        for p in players
    ]


# ── Teams ────────────────────────────────────────────────────────────

@router.get("/teams", response_model=list[DashboardTeamItem], dependencies=[api_key])
def get_teams(
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(TeamModel)
    if search:
        q = q.filter(TeamModel.name.ilike(f"%{search}%"))
    teams = q.order_by(TeamModel.name).offset(offset).limit(limit).all()
    return [
        DashboardTeamItem(
            id=t.id, name=t.name, description=t.description,
            playerCount=t.playerCount, isDefault=t.isDefault,
        )
        for t in teams
    ]


# ── Matches ──────────────────────────────────────────────────────────

@router.get("/matches", response_model=list[DashboardMatchItem], dependencies=[api_key])
def get_matches(
    teamId: Optional[int] = Query(None),
    state: Optional[str] = Query(None),
    leagueId: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(MatchModel)
    if teamId:
        from sqlalchemy import or_
        q = q.filter(or_(MatchModel.team1Id == teamId, MatchModel.team2Id == teamId))
    if state:
        q = q.filter(MatchModel.state == state)
    if leagueId:
        q = q.filter(MatchModel.leagueId == leagueId)
    matches = q.order_by(MatchModel.timestamp.desc()).offset(offset).limit(limit).all()
    return [
        DashboardMatchItem(
            id=m.id, team1Id=m.team1Id, team2Id=m.team2Id,
            team1Name=m.team1Name, team2Name=m.team2Name,
            location=m.location, timestamp=m.timestamp,
            scoreTeam1=m.scoreTeam1, scoreTeam2=m.scoreTeam2,
            state=str(m.state), leagueName=m.leagueName,
            round=m.round,
        )
        for m in matches
    ]


# ── Goals ────────────────────────────────────────────────────────────

@router.get("/goals", response_model=list[DashboardGoalItem], dependencies=[api_key])
def get_goals(
    matchId: Optional[int] = Query(None),
    playerId: Optional[int] = Query(None),
    teamId: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(GoalModel)
    if matchId:
        q = q.filter(GoalModel.matchId == matchId)
    if playerId:
        q = q.filter(GoalModel.playerId == playerId)
    if teamId:
        q = q.filter(GoalModel.teamId == teamId)
    goals = q.order_by(GoalModel.timestamp.desc()).offset(offset).limit(limit).all()
    return [
        DashboardGoalItem(
            id=g.id, matchId=g.matchId, playerId=g.playerId,
            playerName=g.playerName, assistPlayerId=g.assistPlayerId,
            assistPlayerName=g.assistPlayerName, teamId=g.teamId,
            teamName=g.teamName, minute=g.minute,
        )
        for g in goals
    ]


# ── Tournaments ──────────────────────────────────────────────────────

@router.get("/tournaments", response_model=list[DashboardTournamentItem], dependencies=[api_key])
def get_tournaments(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    tournaments = db.query(TournamentModel).order_by(TournamentModel.name).offset(offset).limit(limit).all()
    return [
        DashboardTournamentItem(
            id=t.id, name=t.name, description=t.description,
            formatType=str(t.formatType) if t.formatType else None,
            groupCount=t.groupCount, teamsPerGroup=t.teamsPerGroup,
            hasKnockout=t.hasKnockout,
        )
        for t in tournaments
    ]


# ── Leagues ──────────────────────────────────────────────────────────

@router.get("/leagues", response_model=list[DashboardLeagueItem], dependencies=[api_key])
def get_leagues(
    tournamentId: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(LeagueModel)
    if tournamentId:
        q = q.filter(LeagueModel.tournamentId == tournamentId)
    leagues = q.order_by(LeagueModel.relevanceOrder).offset(offset).limit(limit).all()
    return [
        DashboardLeagueItem(
            id=l.id, name=l.name, season=l.season,
            relevanceOrder=l.relevanceOrder, tournamentId=l.tournamentId,
            startDate=l.startDate, endDate=l.endDate,
        )
        for l in leagues
    ]


# ── Rankings ─────────────────────────────────────────────────────────

@router.get("/rankings", response_model=list[DashboardRankingItem], dependencies=[api_key])
def get_rankings(
    leagueId: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(RankingModel).options(joinedload(RankingModel.team))
    if leagueId:
        q = q.filter(RankingModel.leagueId == leagueId)
    rankings = q.order_by(RankingModel.points.desc()).offset(offset).limit(limit).all()
    return [
        DashboardRankingItem(
            id=r.id, teamId=r.teamId,
            teamName=r.team.name if r.team else None,
            leagueId=r.leagueId, points=r.points,
            gamesPlayed=r.gamesPlayed, gamesWon=r.gamesWon,
            gamesLost=r.gamesLost, gamesTied=r.gamesTied,
            goalsScored=r.goalsScored, goalsConceded=r.goalsConceded,
        )
        for r in rankings
    ]


# ── Training Sessions ───────────────────────────────────────────────

@router.get("/trainings", response_model=list[DashboardTrainingItem], dependencies=[api_key])
def get_trainings(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    trainings = db.query(TrainingSessionModel).order_by(
        TrainingSessionModel.timestamp.desc()
    ).offset(offset).limit(limit).all()
    return [
        DashboardTrainingItem(
            id=t.id, timestamp=t.timestamp,
            location=t.location, details=t.details,
        )
        for t in trainings
    ]


# ── Attendance ───────────────────────────────────────────────────────

@router.get("/attendance", response_model=list[DashboardAttendanceItem], dependencies=[api_key])
def get_attendance(
    matchId: Optional[int] = Query(None),
    playerId: Optional[int] = Query(None),
    teamId: Optional[int] = Query(None),
    scope: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(AttendanceModel)
    if matchId:
        q = q.filter(AttendanceModel.matchId == matchId)
    if playerId:
        q = q.filter(AttendanceModel.playerId == playerId)
    if teamId:
        q = q.filter(AttendanceModel.teamId == teamId)
    if scope:
        q = q.filter(AttendanceModel.scope == scope)
    items = q.order_by(AttendanceModel.recordedAt.desc()).offset(offset).limit(limit).all()
    return [
        DashboardAttendanceItem(
            id=a.id, scope=str(a.scope), matchId=a.matchId,
            trainingSessionId=a.trainingSessionId, tournamentId=a.tournamentId,
            playerId=a.playerId, playerName=a.playerName,
            teamId=a.teamId, status=str(a.status),
            recordedAt=a.recordedAt,
        )
        for a in items
    ]


# ── Notifications ────────────────────────────────────────────────────

@router.get("/notifications", response_model=list[DashboardNotificationItem], dependencies=[api_key])
def get_notifications(
    userId: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(NotificationModel).filter(NotificationModel.isDeleted.is_(False))
    if userId:
        q = q.filter(NotificationModel.userId == userId)
    notifications = q.order_by(NotificationModel.createdAt.desc()).offset(offset).limit(limit).all()
    return [
        DashboardNotificationItem(
            id=n.id, name=n.name, description=n.description,
            userId=n.userId, type=str(n.type),
            createdAt=n.createdAt,
        )
        for n in notifications
    ]
