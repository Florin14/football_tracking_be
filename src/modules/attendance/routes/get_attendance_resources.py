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
from modules.tournament.models.tournament_model import TournamentModel
from modules.team.models.team_model import TeamModel
from .attendance_grouping import build_grouped_attendance
from .router import router


@router.get("-resources", response_model=AttendanceGroupedListResponse)
async def get_attendance_resources(
        skip: int = 0,
        limit: int = 100,
        scope: Optional[str] = None,
        match_id: Optional[int] = None,
        player_id: Optional[int] = None,
        team_id: Optional[int] = None,
        league_id: Optional[int] = None,
        tournament_id: Optional[int] = None,
        training_session_id: Optional[int] = None,
        status: Optional[str] = None,
        db: Session = Depends(get_db)
):
    query = db.query(AttendanceModel)

    # Get default basecamp team
    if team_id is None:
        default_team = db.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()
        if default_team:
            team_id = default_team.id

    # Filter by basecamp team
    if team_id:
        query = query.filter(AttendanceModel.teamId == team_id)

    # Filter to get only matches that are NOT part of tournaments with groups
    query = query.outerjoin(MatchModel, AttendanceModel.matchId == MatchModel.id)
    query = query.outerjoin(LeagueModel, MatchModel.leagueId == LeagueModel.id)
    query = query.outerjoin(TournamentModel, LeagueModel.tournamentId == TournamentModel.id)
    
    query = query.filter(
        or_(
            TournamentModel.groupCount.is_(None),
            TournamentModel.groupCount == 0
        )
    )

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

    if training_session_id:
        query = query.filter(AttendanceModel.trainingSessionId == training_session_id)

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
        query = query.filter(MatchModel.leagueId == league_id)

    if tournament_id:
        query = query.filter(LeagueModel.tournamentId == tournament_id)

    attendance_rows = query.order_by(AttendanceModel.recordedAt.desc()).offset(skip).limit(limit).all()

    grouped_items = build_grouped_attendance(attendance_rows, db)

    return AttendanceGroupedListResponse(data=grouped_items)
