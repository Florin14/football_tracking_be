from sqlalchemy.orm import Session

from constants.attendance_scope import AttendanceScope
from constants.attendance_status import AttendanceStatus
from modules.attendance.models.attendance_model import AttendanceModel
from modules.match.models.match_model import MatchModel
from modules.team.models import TeamModel


def ensure_match_attendance_for_default_team(db: Session, match: MatchModel) -> None:
    from modules.player.models.player_model import PlayerModel
    if not match:
        return

    default_team = db.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()
    if not default_team:
        return

    if match.team1Id != default_team.id and match.team2Id != default_team.id:
        return

    players = (
        db.query(PlayerModel.id, PlayerModel.teamId)
        .filter(PlayerModel.teamId == default_team.id)
        .all()
    )
    if not players:
        return

    player_ids = [player_id for player_id, _ in players]
    existing = {
        row[0]
        for row in db.query(AttendanceModel.playerId)
        .filter(
            AttendanceModel.scope == AttendanceScope.MATCH,
            AttendanceModel.matchId == match.id,
            AttendanceModel.playerId.in_(player_ids),
        )
        .all()
    }
    missing = [
        AttendanceModel(
            scope=AttendanceScope.MATCH,
            matchId=match.id,
            playerId=player_id,
            teamId=team_id,
            status=AttendanceStatus.UNKNOWN,
        )
        for player_id, team_id in players
        if player_id not in existing
    ]
    if missing:
        db.bulk_save_objects(missing)
