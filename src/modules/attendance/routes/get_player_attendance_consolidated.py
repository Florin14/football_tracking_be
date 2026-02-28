from datetime import datetime
from typing import Optional

from fastapi import Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, aliased

from constants.tournament_format_type import TournamentFormatType
from extensions.sqlalchemy import get_db
from project_helpers.dependencies import JwtRequired
from modules.attendance.models.attendance_model import AttendanceModel
from modules.attendance.models.attendance_schemas import (
    AttendanceResponse,
    PlayerAttendanceConsolidatedResponse,
)
from modules.match.models.match_model import MatchModel
from modules.match.models.match_schemas import MatchItem
from modules.team.models.team_model import TeamModel
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.tournament_model import TournamentModel
from modules.tournament.models.tournament_schemas import TournamentItem
from modules.training.models.training_session_model import TrainingSessionModel
from modules.training.models.training_schemas import TrainingSessionResponse
from .router import router


def _build_flat_attendance(attendance_rows, db):
    player_cache = {}
    team_cache = {}
    match_cache = {}
    league_cache = {}
    from modules.player.models.player_model import PlayerModel

    results = []
    for attendance in attendance_rows:
        if attendance.playerId not in player_cache:
            player = db.query(PlayerModel).filter(PlayerModel.id == attendance.playerId).first()
            player_cache[attendance.playerId] = player
        else:
            player = player_cache[attendance.playerId]

        if attendance.teamId not in team_cache:
            team = db.query(TeamModel).filter(TeamModel.id == attendance.teamId).first()
            team_cache[attendance.teamId] = team
        else:
            team = team_cache[attendance.teamId]

        match = None
        if attendance.matchId:
            if attendance.matchId not in match_cache:
                match = db.query(MatchModel).filter(MatchModel.id == attendance.matchId).first()
                match_cache[attendance.matchId] = match
            else:
                match = match_cache[attendance.matchId]

        league_id_value = match.leagueId if match else None
        tournament_id_value = None
        if league_id_value:
            if league_id_value not in league_cache:
                league = db.query(LeagueModel).filter(LeagueModel.id == league_id_value).first()
                league_cache[league_id_value] = league
            else:
                league = league_cache[league_id_value]
            tournament_id_value = league.tournamentId if league else None
        if attendance.tournamentId:
            tournament_id_value = attendance.tournamentId

        results.append(AttendanceResponse(
            id=attendance.id,
            scope=attendance.scope.value,
            matchId=attendance.matchId,
            trainingSessionId=attendance.trainingSessionId,
            playerId=attendance.playerId,
            playerName=player.name if player else "Unknown",
            teamId=attendance.teamId,
            teamName=team.name if team else "Unknown",
            status=attendance.status.value,
            note=attendance.note,
            recordedAt=attendance.recordedAt,
            leagueId=league_id_value,
            tournamentId=tournament_id_value,
        ))

    return results


@router.get(
    "-resources/player",
    response_model=PlayerAttendanceConsolidatedResponse,
    dependencies=[Depends(JwtRequired())],
)
async def get_player_attendance_consolidated(
    playerId: int = Query(...),
    teamId: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    # Resolve team
    resolved_team_id = teamId
    if resolved_team_id is None:
        default_team = db.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()
        if default_team:
            resolved_team_id = default_team.id

    # --- Matches: same logic as get_all_attendance_matches ---
    league_alias = aliased(LeagueModel)
    tournament_alias = aliased(TournamentModel)

    matches_query = (
        db.query(MatchModel)
        .outerjoin(league_alias, MatchModel.leagueId == league_alias.id)
        .outerjoin(tournament_alias, league_alias.tournamentId == tournament_alias.id)
        .options(
            joinedload(MatchModel.team1),
            joinedload(MatchModel.team2),
            joinedload(MatchModel.league),
        )
        .filter(
            or_(
                tournament_alias.formatType.in_([None, TournamentFormatType.LEAGUE]),
                tournament_alias.formatType.notin_(
                    [TournamentFormatType.GROUPS, TournamentFormatType.GROUPS_KNOCKOUT]
                ),
            )
        )
    )

    if resolved_team_id:
        matches_query = matches_query.filter(
            or_(MatchModel.team1Id == resolved_team_id, MatchModel.team2Id == resolved_team_id)
        )

    matches_query = matches_query.order_by(
        MatchModel.timestamp.is_(None),
        MatchModel.timestamp,
        MatchModel.id,
    )
    match_rows = matches_query.all()
    match_rows = sorted(
        match_rows,
        key=lambda m: (m.timestamp is None, m.timestamp or datetime.max),
    )
    matches = [MatchItem.model_validate(m) for m in match_rows]

    # --- Tournaments: all with a non-null formatType ---
    tournament_rows = (
        db.query(TournamentModel)
        .filter(TournamentModel.formatType.notin_([None, TournamentFormatType.LEAGUE]))
        .order_by(TournamentModel.name)
        .all()
    )
    tournaments = [TournamentItem.model_validate(t) for t in tournament_rows]

    # --- Trainings: all, ordered by timestamp desc ---
    training_rows = (
        db.query(TrainingSessionModel)
        .order_by(TrainingSessionModel.timestamp.desc())
        .all()
    )
    trainings = [TrainingSessionResponse.model_validate(t) for t in training_rows]

    # --- Attendance: for this player, filtering out group tournament matches ---
    attendance_query = db.query(AttendanceModel).filter(
        AttendanceModel.playerId == playerId,
    )

    if resolved_team_id:
        attendance_query = attendance_query.filter(AttendanceModel.teamId == resolved_team_id)

    # Exclude attendance records linked to tournaments with NULL formatType
    # (keep all records for tournaments with any non-null format)
    att_direct_tournament = aliased(TournamentModel)

    attendance_query = (
        attendance_query
        .outerjoin(att_direct_tournament, AttendanceModel.tournamentId == att_direct_tournament.id)
        .filter(
            or_(
                AttendanceModel.tournamentId.in_([None, TournamentFormatType.LEAGUE.value]),
                att_direct_tournament.formatType.isnot(None),
            )
        )
    )

    attendance_rows = attendance_query.order_by(AttendanceModel.recordedAt.desc()).all()
    attendance = _build_flat_attendance(attendance_rows, db)

    return PlayerAttendanceConsolidatedResponse(
        matches=matches,
        tournaments=tournaments,
        trainings=trainings,
        attendance=attendance,
    )
