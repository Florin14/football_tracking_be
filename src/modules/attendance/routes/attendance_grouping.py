from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from modules.attendance.models.attendance_model import AttendanceModel
from modules.attendance.models.attendance_schemas import (
    AttendancePlayerGroupResponse,
    AttendanceResponse,
    AttendanceTournamentGroupResponse,
)
from constants.attendance_status import AttendanceStatus
from modules.match.models import MatchModel
from modules.team.models import TeamModel
from modules.tournament.models.league_model import LeagueModel


def build_grouped_attendance(
    attendance_rows: List[AttendanceModel],
    db: Session,
) -> List[AttendancePlayerGroupResponse]:
    from modules.player.models.player_model import PlayerModel

    player_cache: Dict[int, Optional[PlayerModel]] = {}
    team_cache: Dict[int, Optional[TeamModel]] = {}
    match_cache: Dict[int, Optional[MatchModel]] = {}
    league_cache: Dict[int, Optional[LeagueModel]] = {}

    players: Dict[int, AttendancePlayerGroupResponse] = {}
    player_tournaments: Dict[int, Dict[Optional[int], AttendanceTournamentGroupResponse]] = {}

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

        attendance_response = AttendanceResponse(
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
        )

        player_group = players.get(attendance.playerId)
        if player_group is None:
            player_group = AttendancePlayerGroupResponse(
                playerId=attendance.playerId,
                playerName=player.name if player else "Unknown",
                tournaments=[],
            )
            players[attendance.playerId] = player_group
            player_tournaments[attendance.playerId] = {}

        tournament_groups = player_tournaments[attendance.playerId]
        tournament_group = tournament_groups.get(tournament_id_value)
        if tournament_group is None:
            tournament_group = AttendanceTournamentGroupResponse(
                tournamentId=tournament_id_value,
                items=[],
            )
            tournament_groups[tournament_id_value] = tournament_group
            player_group.tournaments.append(tournament_group)

        tournament_group.items.append(attendance_response)

    player_groups = list(players.values())
    player_groups.sort(
        key=lambda group: (
            not any(
                item.status == AttendanceStatus.PRESENT.value
                for tournament in group.tournaments
                for item in tournament.items
            ),
            (group.playerName or "").casefold(),
        )
    )
    return player_groups
