from datetime import datetime

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from constants.attendance_scope import AttendanceScope
from constants.attendance_status import AttendanceStatus
from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.attendance.models.attendance_schemas import AttendanceResponse, AttendanceUpsert
from modules.match.models.match_model import MatchModel
from modules.attendance.models.attendance_model import AttendanceModel
from modules.team.models import TeamModel
from modules.tournament.models.tournament_model import TournamentModel
from modules.training.models import TrainingSessionModel
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.league_team_model import LeagueTeamModel
from project_helpers.dependencies import JwtRequired
from project_helpers.error import Error
from project_helpers.exceptions import ErrorException
from .router import router


@router.post("", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(JwtRequired())])
async def upsert_attendance(
    data: AttendanceUpsert,
    request: Request,
    db: Session = Depends(get_db),
):
    auth_user = request.state.user
    if auth_user.role == PlatformRoles.PLAYER and data.playerId != auth_user.id:
        raise ErrorException(error=Error.USER_UNAUTHORIZED, statusCode=403)
    try:
        scope = AttendanceScope(data.scope.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid attendance scope"
        )

    match = None
    tournament = None
    league = None
    training_session = None

    if scope == AttendanceScope.MATCH:
        if not data.matchId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="matchId is required for MATCH attendance"
            )
        match = db.query(MatchModel).filter(MatchModel.id == data.matchId).first()
        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Match with ID {data.matchId} not found"
            )

    if scope == AttendanceScope.TOURNAMENT:
        if not data.tournamentId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tournamentId is required for TOURNAMENT attendance"
            )
        tournament = db.query(TournamentModel).filter(TournamentModel.id == data.tournamentId).first()
        if not tournament:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tournament with ID {data.tournamentId} not found"
            )

    if scope == AttendanceScope.TRAINING:
        if not data.trainingSessionId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="trainingSessionId is required for TRAINING attendance"
            )
        training_session = db.query(TrainingSessionModel).filter(
            TrainingSessionModel.id == data.trainingSessionId
        ).first()
        if not training_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Training session with ID {data.trainingSessionId} not found"
            )
    from modules.player.models.player_model import PlayerModel

    player = db.query(PlayerModel).filter(PlayerModel.id == data.playerId).first()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player with ID {data.playerId} not found"
        )

    team_id = data.teamId or player.teamId
    team = db.query(TeamModel).filter(TeamModel.id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID {team_id} not found"
        )

    if scope == AttendanceScope.MATCH:
        if team_id not in [match.team1Id, match.team2Id]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team {team.name} is not participating in this match"
            )

    if scope == AttendanceScope.TOURNAMENT:
        league = (
            db.query(LeagueModel)
            .join(LeagueTeamModel, LeagueTeamModel.leagueId == LeagueModel.id)
            .filter(
                LeagueTeamModel.teamId == team.id,
                LeagueModel.tournamentId == tournament.id,
            )
            .first()
        )
        if not league:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team {team.name} is not part of this tournament"
            )

    if player.teamId != team_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Player {player.name} does not belong to team {team.name}"
        )

    try:
        attendance_status = AttendanceStatus(data.status.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid attendance status"
        )

    attendance = None
    if scope == AttendanceScope.MATCH:
        attendance = db.query(AttendanceModel).filter(
            AttendanceModel.scope == scope,
            AttendanceModel.matchId == data.matchId,
            AttendanceModel.playerId == data.playerId
        ).first()
    elif scope == AttendanceScope.TOURNAMENT:
        attendance = db.query(AttendanceModel).filter(
            AttendanceModel.scope == scope,
            AttendanceModel.tournamentId == data.tournamentId,
            AttendanceModel.playerId == data.playerId
        ).first()
    elif scope == AttendanceScope.TRAINING:
        attendance = db.query(AttendanceModel).filter(
            AttendanceModel.scope == scope,
            AttendanceModel.trainingSessionId == data.trainingSessionId,
            AttendanceModel.playerId == data.playerId
        ).first()

    if attendance:
        attendance.status = attendance_status
        attendance.note = data.note
        attendance.teamId = team_id
        attendance.recordedAt = datetime.utcnow()
    else:
        attendance = AttendanceModel(
            scope=scope,
            matchId=data.matchId if scope == AttendanceScope.MATCH else None,
            tournamentId=data.tournamentId if scope == AttendanceScope.TOURNAMENT else None,
            trainingSessionId=data.trainingSessionId if scope == AttendanceScope.TRAINING else None,
            playerId=data.playerId,
            teamId=team_id,
            status=attendance_status,
            note=data.note
        )
        db.add(attendance)

    db.commit()

    league_id = None
    tournament_id = None
    if scope == AttendanceScope.MATCH and match:
        league_id = match.leagueId
        if league_id:
            league = db.query(LeagueModel).filter(LeagueModel.id == league_id).first()
            tournament_id = league.tournamentId if league else None
    if scope == AttendanceScope.TOURNAMENT and tournament:
        tournament_id = tournament.id
        if league:
            league_id = league.id

    attendance._resolvedLeagueId = league_id
    attendance._resolvedTournamentId = tournament_id

    return attendance
