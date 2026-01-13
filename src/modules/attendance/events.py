from typing import Optional

from sqlalchemy import event, exists, func, insert, literal, select, and_
from sqlalchemy.orm import Session

from constants.attendance_scope import AttendanceScope
from constants.attendance_status import AttendanceStatus
from modules.attendance.models.attendance_model import AttendanceModel
from modules.player.models.player_model import PlayerModel
from modules.tournament.models.tournament_model import TournamentModel
from modules.training.models.training_session_model import TrainingSessionModel


def _insert_attendance_for_players(
    connection,
    scope: AttendanceScope,
    tournament_id: Optional[int] = None,
    training_session_id: Optional[int] = None,
):
    attendance_table = AttendanceModel.__table__
    players_table = PlayerModel.__table__

    exists_conditions = [
        attendance_table.c.playerId == players_table.c.id,
        attendance_table.c.scope == scope.value,
    ]
    if tournament_id is not None:
        exists_conditions.append(attendance_table.c.tournamentId == tournament_id)
    if training_session_id is not None:
        exists_conditions.append(attendance_table.c.training_session_id == training_session_id)

    select_stmt = select(
        literal(scope.value),
        literal(tournament_id),
        literal(training_session_id),
        players_table.c.id,
        players_table.c.teamId,
        literal(AttendanceStatus.UNKNOWN.value),
        func.now(),
    ).where(~exists(select(attendance_table.c.id).where(and_(*exists_conditions))))

    insert_stmt = insert(attendance_table).from_select(
        [
            attendance_table.c.scope,
            attendance_table.c.tournamentId,
        attendance_table.c.training_session_id,
            attendance_table.c.playerId,
            attendance_table.c.teamId,
            attendance_table.c.status,
            attendance_table.c.recordedAt,
        ],
        select_stmt,
    )
    connection.execute(insert_stmt)


def backfill_attendance_for_existing_scopes(db: Session) -> None:
    players = db.query(PlayerModel.id, PlayerModel.teamId).all()
    if not players:
        return

    tournaments = db.query(TournamentModel.id).all()
    for (tournament_id,) in tournaments:
        existing_player_ids = {
            row[0]
            for row in db.query(AttendanceModel.playerId)
            .filter(
                AttendanceModel.scope == AttendanceScope.TOURNAMENT,
                AttendanceModel.tournamentId == tournament_id,
            )
            .all()
        }
        missing = [
            AttendanceModel(
                scope=AttendanceScope.TOURNAMENT,
                tournamentId=tournament_id,
                playerId=player_id,
                teamId=team_id,
                status=AttendanceStatus.UNKNOWN,
            )
            for player_id, team_id in players
            if player_id not in existing_player_ids
        ]
        if missing:
            db.bulk_save_objects(missing)

    training_sessions = db.query(TrainingSessionModel.id).all()
    for (training_session_id,) in training_sessions:
        existing_player_ids = {
            row[0]
            for row in db.query(AttendanceModel.playerId)
            .filter(
                AttendanceModel.scope == AttendanceScope.TRAINING,
                AttendanceModel.trainingSessionId == training_session_id,
            )
            .all()
        }
        missing = [
            AttendanceModel(
                scope=AttendanceScope.TRAINING,
                trainingSessionId=training_session_id,
                playerId=player_id,
                teamId=team_id,
                status=AttendanceStatus.UNKNOWN,
            )
            for player_id, team_id in players
            if player_id not in existing_player_ids
        ]
        if missing:
            db.bulk_save_objects(missing)

    db.commit()


@event.listens_for(TournamentModel, "after_insert")
def create_tournament_attendance(mapper, connection, target):
    _insert_attendance_for_players(
        connection,
        AttendanceScope.TOURNAMENT,
        tournament_id=target.id,
    )


@event.listens_for(TrainingSessionModel, "after_insert")
def create_training_attendance(mapper, connection, target):
    _insert_attendance_for_players(
        connection,
        AttendanceScope.TRAINING,
        training_session_id=target.id,
    )
