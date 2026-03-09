from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from constants.attendance_scope import AttendanceScope
from constants.attendance_status import AttendanceStatus
from modules.attendance.models.attendance_model import AttendanceModel
from modules.team.models import TeamModel

if TYPE_CHECKING:
    from modules.match.models.match_model import MatchModel
    from modules.player.models.player_model import PlayerModel

logger = logging.getLogger(__name__)


def create_attendance_for_new_player(db: Session, player: PlayerModel) -> None:
    """Create attendance records for a new player for all existing events."""
    from modules.match.models.match_model import MatchModel as MatchMdl
    from modules.tournament.models.tournament_model import TournamentModel
    from modules.training.models.training_session_model import TrainingSessionModel

    player_id = player.id
    team_id = player.teamId
    created = 0

    # 1. Tournaments
    tournament_ids = [tid for (tid,) in db.query(TournamentModel.id).all()]
    if tournament_ids:
        existing = {
            row[0]
            for row in db.query(AttendanceModel.tournamentId)
            .filter(
                AttendanceModel.scope == AttendanceScope.TOURNAMENT,
                AttendanceModel.playerId == player_id,
            )
            .all()
        }
        missing = [
            AttendanceModel(
                scope=AttendanceScope.TOURNAMENT,
                tournamentId=tid,
                playerId=player_id,
                teamId=team_id,
                status=AttendanceStatus.UNKNOWN,
            )
            for tid in tournament_ids
            if tid not in existing
        ]
        if missing:
            db.bulk_save_objects(missing)
            created += len(missing)

    # 2. Training sessions
    training_ids = [tid for (tid,) in db.query(TrainingSessionModel.id).all()]
    if training_ids:
        existing = {
            row[0]
            for row in db.query(AttendanceModel.trainingSessionId)
            .filter(
                AttendanceModel.scope == AttendanceScope.TRAINING,
                AttendanceModel.playerId == player_id,
            )
            .all()
        }
        missing = [
            AttendanceModel(
                scope=AttendanceScope.TRAINING,
                trainingSessionId=tid,
                playerId=player_id,
                teamId=team_id,
                status=AttendanceStatus.UNKNOWN,
            )
            for tid in training_ids
            if tid not in existing
        ]
        if missing:
            db.bulk_save_objects(missing)
            created += len(missing)

    # 3. Matches involving the player's team (all states)
    default_team = db.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()
    if default_team and team_id == default_team.id:
        match_ids = [
            mid
            for (mid,) in db.query(MatchMdl.id)
            .filter(
                (MatchMdl.team1Id == default_team.id) | (MatchMdl.team2Id == default_team.id),
            )
            .all()
        ]
        if match_ids:
            existing = {
                row[0]
                for row in db.query(AttendanceModel.matchId)
                .filter(
                    AttendanceModel.scope == AttendanceScope.MATCH,
                    AttendanceModel.playerId == player_id,
                )
                .all()
            }
            missing = [
                AttendanceModel(
                    scope=AttendanceScope.MATCH,
                    matchId=mid,
                    playerId=player_id,
                    teamId=team_id,
                    status=AttendanceStatus.UNKNOWN,
                )
                for mid in match_ids
                if mid not in existing
            ]
            if missing:
                db.bulk_save_objects(missing)
                created += len(missing)

    if created:
        logger.info("Created %d attendance records for new player %s (id=%s).", created, player.name, player_id)


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
