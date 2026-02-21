from fastapi import Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, aliased

from constants.attendance_scope import AttendanceScope
from constants.tournament_format_type import TournamentFormatType
from extensions.sqlalchemy import get_db
from project_helpers.dependencies import JwtRequired
from modules.attendance.models.attendance_model import AttendanceModel
from modules.attendance.models.attendance_schemas import (
    AttendanceExportResponse,
    ExportEventColumn,
    ExportPlayerRow,
)
from modules.match.models.match_model import MatchModel
from modules.player.models.player_model import PlayerModel
from modules.team.models.team_model import TeamModel
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.tournament_model import TournamentModel
from modules.training.models.training_session_model import TrainingSessionModel
from .router import router


@router.get(
    "/export-data",
    response_model=AttendanceExportResponse,
    dependencies=[Depends(JwtRequired())],
)
async def get_attendance_export_data(
    teamId: int = Query(None),
    db: Session = Depends(get_db),
):
    # 1. Resolve baseCamp team
    resolved_team_id = teamId
    if resolved_team_id is None:
        default_team = db.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()
        if default_team:
            resolved_team_id = default_team.id

    # 2. Query matches (reuse group-tournament exclusion filter)
    league_alias = aliased(LeagueModel)
    tournament_alias = aliased(TournamentModel)

    matches_query = (
        db.query(MatchModel)
        .outerjoin(league_alias, MatchModel.leagueId == league_alias.id)
        .outerjoin(tournament_alias, league_alias.tournamentId == tournament_alias.id)
        .options(
            joinedload(MatchModel.team1),
            joinedload(MatchModel.team2),
        )
        .filter(
            or_(
                tournament_alias.formatType.is_(None),
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

    match_rows = matches_query.all()

    # 3. Query all training sessions
    training_rows = db.query(TrainingSessionModel).all()

    # 4. Build unified event list sorted by timestamp ascending
    events = []

    for m in match_rows:
        # Determine opponent name
        if resolved_team_id and m.team1Id == resolved_team_id:
            opponent = m.team2.name if m.team2 else "Unknown"
        elif resolved_team_id and m.team2Id == resolved_team_id:
            opponent = m.team1.name if m.team1 else "Unknown"
        else:
            opponent = f"{m.team1Name or 'Unknown'} vs {m.team2Name or 'Unknown'}"

        date_str = m.timestamp.strftime("%d.%m.%Y") if m.timestamp else ""
        events.append({
            "type": "MATCH",
            "label": opponent,
            "date": date_str,
            "eventId": m.id,
            "timestamp": m.timestamp,
        })

    for tr in training_rows:
        date_str = tr.timestamp.strftime("%d.%m.%Y") if tr.timestamp else ""
        events.append({
            "type": "TRAINING",
            "label": "ANTRENAMENT",
            "date": date_str,
            "eventId": tr.id,
            "timestamp": tr.timestamp,
        })

    # Sort all events by timestamp ascending (None last)
    events.sort(key=lambda e: (e["timestamp"] is None, e["timestamp"] or ""))

    columns = [
        ExportEventColumn(
            type=e["type"],
            label=e["label"],
            date=e["date"],
            eventId=e["eventId"],
        )
        for e in events
    ]

    # 5. Query players in the baseCamp team, sorted by name
    players_query = db.query(PlayerModel).order_by(PlayerModel.name)
    if resolved_team_id:
        players_query = players_query.filter(PlayerModel.teamId == resolved_team_id)
    player_rows = players_query.all()

    # 6. Query all MATCH + TRAINING attendance records for the team
    att_query = db.query(AttendanceModel).filter(
        AttendanceModel.scope.in_([AttendanceScope.MATCH, AttendanceScope.TRAINING])
    )
    if resolved_team_id:
        att_query = att_query.filter(AttendanceModel.teamId == resolved_team_id)
    attendance_rows = att_query.all()

    # 7. Build lookup (playerId, scope, eventId) → status
    lookup = {}
    for att in attendance_rows:
        scope_val = att.scope.value if hasattr(att.scope, "value") else att.scope
        if scope_val == "MATCH" and att.matchId:
            lookup[(att.playerId, "MATCH", att.matchId)] = att.status.value if hasattr(att.status, "value") else att.status
        elif scope_val == "TRAINING" and att.trainingSessionId:
            lookup[(att.playerId, "TRAINING", att.trainingSessionId)] = att.status.value if hasattr(att.status, "value") else att.status

    # 8. Assemble response
    players = []
    for p in player_rows:
        statuses = []
        for e in events:
            key = (p.id, e["type"], e["eventId"])
            statuses.append(lookup.get(key))
        players.append(ExportPlayerRow(
            playerId=p.id,
            playerName=p.name,
            statuses=statuses,
        ))

    return AttendanceExportResponse(columns=columns, players=players)
