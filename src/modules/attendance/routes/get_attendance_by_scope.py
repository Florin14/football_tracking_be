from typing import Optional

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, aliased

from constants.attendance_scope import AttendanceScope
from constants.attendance_status import AttendanceStatus
from extensions.sqlalchemy import get_db
from modules.attendance.models.attendance_schemas import AttendanceGroupedListResponse
from modules.match.models import MatchModel
from modules.attendance.models.attendance_model import AttendanceModel
from modules.tournament.models.league_model import LeagueModel
from modules.player.models import PlayerModel
from modules.tournament.models.tournament_model import TournamentModel
from .attendance_grouping import build_grouped_attendance
from .router import router


@router.get("-by-scope", response_model=AttendanceGroupedListResponse)
async def get_attendance_by_scope(
        skip: int = 0,
        limit: int = 100,
        scope: Optional[str] = None,
        match_id: Optional[int] = Query(None, alias="matchId"),
        player_id: Optional[int] = Query(None, alias="playerId"),
        team_id: Optional[int] = Query(None, alias="teamId"),
        league_id: Optional[int] = Query(None, alias="leagueId"),
        tournament_id: Optional[int] = Query(None, alias="tournamentId"),
        training_session_id: Optional[int] = Query(None, alias="trainingSessionId"),
        excludeGroupLeagues: bool = Query(False, alias="excludeGroupLeagues"),
        status: Optional[str] = None,
        db: Session = Depends(get_db)
):
    query = db.query(AttendanceModel)

    attendance_scope = None
    if scope:
        try:
            attendance_scope = AttendanceScope(scope.upper())
            query = query.filter(AttendanceModel.scope == attendance_scope)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid attendance scope"
            )

    if match_id:
        query = query.filter(AttendanceModel.matchId == match_id)

    if player_id:
        query = query.filter(AttendanceModel.playerId == player_id)

    if team_id:
        query = query.filter(AttendanceModel.teamId == team_id)

    if training_session_id:
        query = query.filter(AttendanceModel.trainingSessionId == training_session_id)

    attendance_status = None
    if status:
        try:
            attendance_status = AttendanceStatus(status.upper())
            query = query.filter(AttendanceModel.status == attendance_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid attendance status"
            )

    if league_id:
        query = query.join(MatchModel, AttendanceModel.matchId == MatchModel.id)
        query = query.filter(MatchModel.leagueId == league_id)

    if tournament_id:
        query = query.outerjoin(MatchModel, AttendanceModel.matchId == MatchModel.id)
        query = query.outerjoin(LeagueModel, MatchModel.leagueId == LeagueModel.id)
        query = query.filter(
            or_(
                AttendanceModel.tournamentId == tournament_id,
                LeagueModel.tournamentId == tournament_id
            )
        )

    if attendance_scope == AttendanceScope.MATCH and match_id:
        match = db.query(MatchModel).filter(MatchModel.id == match_id).first()
        if match:
            should_add_missing = True
            if team_id and team_id not in (match.team1Id, match.team2Id):
                should_add_missing = False
            if league_id and match.leagueId != league_id:
                should_add_missing = False
            if tournament_id and should_add_missing:
                league = None
                if match.leagueId:
                    league = db.query(LeagueModel).filter(LeagueModel.id == match.leagueId).first()
                if not league or league.tournamentId != tournament_id:
                    should_add_missing = False
            if excludeGroupLeagues and should_add_missing and match.leagueId:
                tournament = (
                    db.query(TournamentModel)
                    .join(LeagueModel, LeagueModel.tournamentId == TournamentModel.id)
                    .filter(LeagueModel.id == match.leagueId)
                    .first()
                )
                if tournament and (tournament.formatType or "").upper().startswith("GROUP"):
                    should_add_missing = False

            if should_add_missing and (attendance_status is None or attendance_status == AttendanceStatus.UNKNOWN):
                players_query = db.query(PlayerModel).filter(
                    PlayerModel.teamId.in_([match.team1Id, match.team2Id])
                )
                if team_id:
                    players_query = players_query.filter(PlayerModel.teamId == team_id)
                if player_id:
                    players_query = players_query.filter(PlayerModel.id == player_id)
                players = players_query.all()
                if players:
                    player_ids = [player.id for player in players]
                    existing_player_ids = {
                        row[0]
                        for row in db.query(AttendanceModel.playerId)
                        .filter(
                            AttendanceModel.scope == AttendanceScope.MATCH,
                            AttendanceModel.matchId == match_id,
                            AttendanceModel.playerId.in_(player_ids),
                        )
                        .all()
                    }
                    missing = [
                        AttendanceModel(
                            scope=AttendanceScope.MATCH,
                            matchId=match_id,
                            playerId=player.id,
                            teamId=player.teamId,
                            status=AttendanceStatus.UNKNOWN,
                        )
                        for player in players
                        if player.id not in existing_player_ids
                    ]
                    if missing:
                        db.bulk_save_objects(missing)
                        db.commit()

    if excludeGroupLeagues:
        direct_tournament = aliased(TournamentModel)
        league_tournament = aliased(TournamentModel)
        match_for_league = aliased(MatchModel)
        league_for_match = aliased(LeagueModel)

        query = query.outerjoin(direct_tournament, AttendanceModel.tournamentId == direct_tournament.id)
        query = query.outerjoin(match_for_league, AttendanceModel.matchId == match_for_league.id)
        query = query.outerjoin(league_for_match, match_for_league.leagueId == league_for_match.id)
        query = query.outerjoin(league_tournament, league_for_match.tournamentId == league_tournament.id)
        query = query.filter(
            or_(
                direct_tournament.formatType.is_(None),
                ~func.upper(direct_tournament.formatType).like("GROUP%"),
            )
        ).filter(
            or_(
                league_tournament.formatType.is_(None),
                ~func.upper(league_tournament.formatType).like("GROUP%"),
            )
        )

    attendance_rows = query.order_by(AttendanceModel.recordedAt.desc()).offset(skip).limit(limit).all()

    grouped_items = build_grouped_attendance(attendance_rows, db)

    return AttendanceGroupedListResponse(data=grouped_items)
