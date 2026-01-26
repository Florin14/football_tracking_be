import re
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from constants.match_state import MatchState
from modules.match.models.match_model import MatchModel
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.league_team_model import LeagueTeamModel
from modules.tournament.models.tournament_knockout_match_model import TournamentKnockoutMatchModel


def _get_match_winner(match: MatchModel) -> int | None:
    if not match or match.state != MatchState.FINISHED:
        return None
    if match.scoreTeam1 is None or match.scoreTeam2 is None:
        return None
    if match.scoreTeam1 == match.scoreTeam2:
        return None
    return match.team1Id if match.scoreTeam1 > match.scoreTeam2 else match.team2Id


def _next_round_label(current_round: str | None, match_count: int) -> str | None:
    if not current_round:
        return None
    round_lower = current_round.strip().lower()
    if round_lower == "final":
        return None
    mapping = {
        "round of 16": "Quarterfinal",
        "round of 8": "Quarterfinal",
        "round of 4": "Semifinal",
        "round of 2": "Final",
        "quarterfinal": "Semifinal",
        "quarter-finals": "Semifinal",
        "semifinal": "Final",
        "semi-final": "Final",
    }
    if round_lower in mapping:
        return mapping[round_lower]
    match = re.match(r"^round of (\d+)$", round_lower)
    if match:
        teams = int(match.group(1))
        if teams <= 2:
            return "Final"
        return f"Round of {max(2, teams // 2)}"
    if match_count >= 2:
        return f"Round of {match_count}"
    return None


def _resolve_common_league_id(db: Session, tournament_id: int, team1_id: int, team2_id: int) -> int | None:
    rows = (
        db.query(LeagueTeamModel.teamId, LeagueTeamModel.leagueId)
        .join(LeagueModel, LeagueModel.id == LeagueTeamModel.leagueId)
        .filter(
            LeagueModel.tournamentId == tournament_id,
            LeagueTeamModel.teamId.in_([team1_id, team2_id]),
        )
        .all()
    )
    team_leagues = {team1_id: set(), team2_id: set()}
    for team_id, league_id in rows:
        team_leagues.setdefault(team_id, set()).add(league_id)
    common = team_leagues.get(team1_id, set()).intersection(team_leagues.get(team2_id, set()))
    if len(common) == 1:
        return next(iter(common))
    return None


def auto_advance_knockout(db: Session, match: MatchModel) -> None:
    knockout_entry = (
        db.query(TournamentKnockoutMatchModel)
        .filter(TournamentKnockoutMatchModel.matchId == match.id)
        .first()
    )
    if not knockout_entry:
        return

    winner = _get_match_winner(match)
    if not winner:
        return

    current_round = knockout_entry.round
    tournament_id = knockout_entry.tournamentId
    current_entries = (
        db.query(TournamentKnockoutMatchModel)
        .filter(
            TournamentKnockoutMatchModel.tournamentId == tournament_id,
            TournamentKnockoutMatchModel.round == current_round,
        )
        .order_by(
            TournamentKnockoutMatchModel.order.is_(None),
            TournamentKnockoutMatchModel.order,
            TournamentKnockoutMatchModel.id,
        )
        .all()
    )
    if not current_entries:
        return

    winners: list[int | None] = []
    for entry in current_entries:
        entry_match = db.query(MatchModel).filter(MatchModel.id == entry.matchId).first()
        winners.append(_get_match_winner(entry_match))

    next_round = _next_round_label(current_round, len(current_entries))
    if not next_round:
        return

    existing_next = (
        db.query(TournamentKnockoutMatchModel)
        .filter(
            TournamentKnockoutMatchModel.tournamentId == tournament_id,
            TournamentKnockoutMatchModel.round == next_round,
        )
        .all()
    )
    existing_by_order = {entry.order: entry for entry in existing_next}

    start_time = datetime.utcnow()
    interval = timedelta(minutes=90)
    for idx in range(0, len(winners), 2):
        order = idx // 2 + 1
        if order in existing_by_order:
            continue
        if idx + 1 >= len(winners):
            continue
        team1_id = winners[idx]
        team2_id = winners[idx + 1]
        if not team1_id or not team2_id:
            continue

        league_id = _resolve_common_league_id(db, tournament_id, team1_id, team2_id)
        new_match = MatchModel(
            team1Id=team1_id,
            team2Id=team2_id,
            timestamp=start_time + interval * (order - 1),
            state=MatchState.SCHEDULED,
            leagueId=league_id,
        )
        db.add(new_match)
        db.flush()
        db.add(TournamentKnockoutMatchModel(
            tournamentId=tournament_id,
            matchId=new_match.id,
            round=next_round,
            order=order,
        ))
