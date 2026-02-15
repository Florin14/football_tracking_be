from fastapi import Depends, HTTPException, status
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session, aliased

from constants.attendance_scope import AttendanceScope
from constants.attendance_status import AttendanceStatus
from extensions.sqlalchemy import get_db
from project_helpers.dependencies import JwtRequired
from modules.attendance.models.attendance_schemas import AttendanceGroupedListResponse, AttendanceQueryParams
from modules.match.models import MatchModel
from modules.attendance.models.attendance_model import AttendanceModel
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.tournament_model import TournamentModel
from modules.team.models.team_model import TeamModel
from .attendance_grouping import build_grouped_attendance
from .router import router


@router.get("", response_model=AttendanceGroupedListResponse, dependencies=[Depends(JwtRequired())])
async def get_attendance(
        params: AttendanceQueryParams = Depends(),
        db: Session = Depends(get_db),
):
    query = db.query(AttendanceModel)

    if params.scope:
        try:
            attendance_scope = AttendanceScope(params.scope.upper())
            query = query.filter(AttendanceModel.scope == attendance_scope)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid attendance scope"
            )

    if params.matchId:
        query = query.filter(AttendanceModel.matchId == params.matchId)

    if params.playerId:
        query = query.filter(AttendanceModel.playerId == params.playerId)

    team_id = params.teamId
    if team_id is None:
        default_team = db.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()
        if default_team:
            team_id = default_team.id

    if team_id:
        query = query.filter(AttendanceModel.teamId == team_id)

    if params.trainingSessionId:
        query = query.filter(AttendanceModel.trainingSessionId == params.trainingSessionId)

    if params.status:
        try:
            attendance_status = AttendanceStatus(params.status.upper())
            query = query.filter(AttendanceModel.status == attendance_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid attendance status"
            )

    if params.leagueId:
        query = query.join(MatchModel, AttendanceModel.matchId == MatchModel.id)
        query = query.filter(MatchModel.leagueId == params.leagueId)

    if params.tournamentId:
        query = query.outerjoin(MatchModel, AttendanceModel.matchId == MatchModel.id)
        query = query.outerjoin(LeagueModel, MatchModel.leagueId == LeagueModel.id)
        query = query.filter(
            or_(
                AttendanceModel.tournamentId == params.tournamentId,
                LeagueModel.tournamentId == params.tournamentId
            )
        )

    if params.excludeGroupLeagues:
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

    attendance_rows = params.apply(
        query.order_by(case((AttendanceModel.status == AttendanceStatus.PRESENT, 0), else_=1), AttendanceModel.recordedAt.desc())
    ).all()

    grouped_items = build_grouped_attendance(attendance_rows, db)

    return AttendanceGroupedListResponse(data=grouped_items)
