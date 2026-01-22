from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from constants.attendance_scope import AttendanceScope
from constants.attendance_status import AttendanceStatus
from extensions.sqlalchemy import get_db
from modules.attendance.models.attendance_schemas import AttendanceGroupedListResponse
from modules.match.models import MatchModel
from modules.attendance.models.attendance_model import AttendanceModel
from modules.tournament.models.league_model import LeagueModel
from .attendance_grouping import build_grouped_attendance
from .router import router


@router.get("", response_model=AttendanceGroupedListResponse)
async def get_attendance(
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

    attendance_rows = query.order_by(AttendanceModel.recordedAt.desc()).offset(skip).limit(limit).all()

    grouped_items = build_grouped_attendance(attendance_rows, db)

    return AttendanceGroupedListResponse(data=grouped_items)
