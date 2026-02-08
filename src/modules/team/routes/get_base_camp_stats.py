from fastapi import Depends
from sqlalchemy import and_, func, or_, desc
from sqlalchemy.orm import Session

from constants.attendance_scope import AttendanceScope
from constants.attendance_status import AttendanceStatus
from extensions.sqlalchemy import get_db
from project_helpers.dependencies import JwtRequired
from modules.attendance.models.attendance_model import AttendanceModel
from modules.match.models.goal_model import GoalModel
from modules.match.models.match_model import MatchModel
from modules.player.models.player_model import PlayerModel
from modules.team.models import BaseCampStatsResponse, PlayerStatItem, TeamModel
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.tournament_model import TournamentModel
from .router import router


def _normal_league_tournament_filter():
    return and_(
        or_(TournamentModel.groupCount.is_(None), TournamentModel.groupCount == 0),
        or_(
            TournamentModel.formatType.is_(None),
            ~func.upper(TournamentModel.formatType).like("GROUP%"),
        ),
    )


@router.get("/base-camp/stats", response_model=BaseCampStatsResponse)
async def get_base_camp_stats(
    db: Session = Depends(get_db),
    current_user=Depends(JwtRequired()),
):
    team = db.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()
    if not team:
        return BaseCampStatsResponse()

    normal_league_filter = _normal_league_tournament_filter()

    top_scorer = (
        db.query(
            PlayerModel.id,
            PlayerModel.name,
            func.count(GoalModel.id).label("value"),
        )
        .join(GoalModel, GoalModel.playerId == PlayerModel.id)
        .join(MatchModel, GoalModel.matchId == MatchModel.id)
        .join(LeagueModel, MatchModel.leagueId == LeagueModel.id)
        .join(TournamentModel, LeagueModel.tournamentId == TournamentModel.id)
        .filter(PlayerModel.teamId == team.id)
        .filter(normal_league_filter)
        .group_by(PlayerModel.id, PlayerModel.name)
        .order_by(desc("value"), PlayerModel.name.asc())
        .first()
    )

    top_appearances = (
        db.query(
            PlayerModel.id,
            PlayerModel.name,
            func.count(AttendanceModel.id).label("value"),
        )
        .join(AttendanceModel, AttendanceModel.playerId == PlayerModel.id)
        .join(MatchModel, AttendanceModel.matchId == MatchModel.id)
        .join(LeagueModel, MatchModel.leagueId == LeagueModel.id)
        .join(TournamentModel, LeagueModel.tournamentId == TournamentModel.id)
        .filter(PlayerModel.teamId == team.id)
        .filter(AttendanceModel.scope == AttendanceScope.MATCH)
        .filter(AttendanceModel.status == AttendanceStatus.PRESENT)
        .filter(normal_league_filter)
        .group_by(PlayerModel.id, PlayerModel.name)
        .order_by(desc("value"), PlayerModel.name.asc())
        .first()
    )

    # Assists are not persisted in DB yet; keep placeholder until the model supports them.
    top_assists = None

    return BaseCampStatsResponse(
        topScorer=PlayerStatItem(
            playerId=top_scorer.id,
            playerName=top_scorer.name,
            value=int(top_scorer.value),
        ) if top_scorer else None,
        topAssists=PlayerStatItem(
            playerId=top_assists.id,
            playerName=top_assists.name,
            value=int(top_assists.value),
        ) if top_assists else None,
        topAppearances=PlayerStatItem(
            playerId=top_appearances.id,
            playerName=top_appearances.name,
            value=int(top_appearances.value),
        ) if top_appearances else None,
    )
