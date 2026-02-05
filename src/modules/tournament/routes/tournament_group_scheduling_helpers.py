import random
import re
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload

from constants.match_state import MatchState
from modules.attendance.services.attendance_service import ensure_match_attendance_for_default_team
from modules.match.models.match_model import MatchModel
from modules.match.services.match_status import is_match_completed, match_is_completed_expr
from modules.team.models.team_model import TeamModel
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.league_team_model import LeagueTeamModel
from modules.tournament.models.tournament_group_match_model import TournamentGroupMatchModel
from modules.tournament.models.tournament_group_model import TournamentGroupModel
from modules.tournament.models.tournament_group_team_model import TournamentGroupTeamModel
from modules.tournament.models.tournament_knockout_match_model import TournamentKnockoutMatchModel
from modules.tournament.models.tournament_model import TournamentModel

PHASE_ORDER = ["RO16", "QF", "SF", "3P", "F"]
DEFAULT_PAIRING_CONFIG = {phase: "CROSS" for phase in PHASE_ORDER}


def _get_tournament_or_404(db: Session, tournament_id: int) -> TournamentModel:
    tournament = db.query(TournamentModel).filter(TournamentModel.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament with ID {tournament_id} not found",
        )
    return tournament


def _get_tournament_teams(db: Session, tournament_id: int) -> list[TeamModel]:
    return (
        db.query(TeamModel)
        .join(LeagueTeamModel, LeagueTeamModel.teamId == TeamModel.id)
        .join(LeagueModel, LeagueModel.id == LeagueTeamModel.leagueId)
        .filter(LeagueModel.tournamentId == tournament_id)
        .order_by(func.lower(TeamModel.name))
        .all()
    )


def _load_groups_with_teams(db: Session, tournament_id: int) -> list[TournamentGroupModel]:
    return (
        db.query(TournamentGroupModel)
        .options(
            joinedload(TournamentGroupModel.teams)
            .joinedload(TournamentGroupTeamModel.team)
        )
        .filter(TournamentGroupModel.tournamentId == tournament_id)
        .order_by(
            TournamentGroupModel.order.is_(None),
            TournamentGroupModel.order,
            func.lower(TournamentGroupModel.name),
        )
        .all()
    )


def _build_group_name(index: int) -> str:
    if index < 26:
        return f"Group {chr(65 + index)}"
    return f"Group {index + 1}"


def _generate_round_robin(team_ids: list[int], randomize: bool) -> list[list[tuple[int, int]]]:
    if len(team_ids) < 2:
        return []

    teams = list(team_ids)
    if randomize:
        random.shuffle(teams)

    if len(teams) % 2 == 1:
        teams.append(None)

    rounds = []
    n = len(teams)
    for _ in range(n - 1):
        pairs = []
        for i in range(n // 2):
            team1 = teams[i]
            team2 = teams[n - 1 - i]
            if team1 is None or team2 is None:
                continue
            if randomize and random.choice([True, False]):
                team1, team2 = team2, team1
            pairs.append((team1, team2))
        rounds.append(pairs)
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]

    return rounds


def _order_matches(match_specs: list[dict], avoid_consecutive: bool) -> list[dict]:
    remaining = list(match_specs)
    random.shuffle(remaining)
    ordered: list[dict] = []
    last_teams: set[int] = set()

    while remaining:
        next_index = None
        if avoid_consecutive:
            for idx, match in enumerate(remaining):
                if match["team1Id"] not in last_teams and match["team2Id"] not in last_teams:
                    next_index = idx
                    break
        if next_index is None:
            next_index = 0
        match = remaining.pop(next_index)
        ordered.append(match)
        last_teams = {match["team1Id"], match["team2Id"]}

    return ordered


def _build_group_standings(group: TournamentGroupModel, matches: list[MatchModel]) -> list[dict]:
    standings: dict[int, dict] = {}
    for group_team in group.teams:
        team = group_team.team
        if not team:
            continue
        standings[team.id] = {
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "logo": team.logo,
            "playerCount": 0,
            "points": 0,
            "goalsFor": 0,
            "goalsAgainst": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
        }

    for match in matches:
        if not is_match_completed(match):
            continue
        team1 = standings.get(match.team1Id)
        team2 = standings.get(match.team2Id)
        if not team1 or not team2:
            continue
        score1 = match.scoreTeam1 or 0
        score2 = match.scoreTeam2 or 0
        team1["goalsFor"] += score1
        team1["goalsAgainst"] += score2
        team2["goalsFor"] += score2
        team2["goalsAgainst"] += score1

        if score1 > score2:
            team1["wins"] += 1
            team2["losses"] += 1
            team1["points"] += 3
        elif score2 > score1:
            team2["wins"] += 1
            team1["losses"] += 1
            team2["points"] += 3
        else:
            team1["draws"] += 1
            team2["draws"] += 1
            team1["points"] += 1
            team2["points"] += 1

    def sort_key(item: dict):
        goal_diff = item["goalsFor"] - item["goalsAgainst"]
        return (-item["points"], -goal_diff, -item["goalsFor"], item["name"].lower())

    return sorted(standings.values(), key=sort_key)


def _get_group_completion_map(db: Session, group_ids: list[int]) -> dict[int, bool]:
    if not group_ids:
        return {}
    rows = (
        db.query(
            TournamentGroupMatchModel.groupId,
            func.count(MatchModel.id),
            func.coalesce(
                func.sum(case((match_is_completed_expr(MatchModel), 1), else_=0)),
                0,
            ),
        )
        .join(MatchModel, TournamentGroupMatchModel.matchId == MatchModel.id)
        .filter(TournamentGroupMatchModel.groupId.in_(group_ids))
        .group_by(TournamentGroupMatchModel.groupId)
        .all()
    )
    completion = {group_id: False for group_id in group_ids}
    for group_id, total_matches, finished_matches in rows:
        completion[group_id] = total_matches > 0 and finished_matches == total_matches
    return completion


def _load_knockout_entries(
    db: Session,
    tournament_id: int,
    round_label: str,
) -> list[TournamentKnockoutMatchModel]:
    return (
        db.query(TournamentKnockoutMatchModel)
        .options(joinedload(TournamentKnockoutMatchModel.match))
        .filter(
            TournamentKnockoutMatchModel.tournamentId == tournament_id,
            TournamentKnockoutMatchModel.round == round_label,
        )
        .order_by(
            TournamentKnockoutMatchModel.order.is_(None),
            TournamentKnockoutMatchModel.order,
            TournamentKnockoutMatchModel.id,
        )
        .all()
    )


def _get_knockout_winners(entries: list[TournamentKnockoutMatchModel]) -> list[int | None]:
    winners: list[int | None] = []
    for entry in entries:
        match = entry.match
        if not is_match_completed(match):
            winners.append(None)
            continue
        if match.scoreTeam1 is None or match.scoreTeam2 is None:
            winners.append(None)
            continue
        if match.scoreTeam1 == match.scoreTeam2:
            winners.append(None)
            continue
        winners.append(match.team1Id if match.scoreTeam1 > match.scoreTeam2 else match.team2Id)
    return winners


def _get_knockout_losers(entries: list[TournamentKnockoutMatchModel]) -> list[int | None]:
    losers: list[int | None] = []
    for entry in entries:
        match = entry.match
        if not is_match_completed(match):
            losers.append(None)
            continue
        if match.scoreTeam1 is None or match.scoreTeam2 is None:
            losers.append(None)
            continue
        if match.scoreTeam1 == match.scoreTeam2:
            losers.append(None)
            continue
        losers.append(match.team2Id if match.scoreTeam1 > match.scoreTeam2 else match.team1Id)
    return losers


def _normalize_pairing_config(pairing_config: dict | None, fallback: str | None) -> dict[str, str]:
    config = DEFAULT_PAIRING_CONFIG.copy()
    if fallback:
        normalized = _normalize_pairing_value(fallback)
        for phase in config:
            config[phase] = normalized
    if pairing_config:
        for key, value in pairing_config.items():
            phase_key = str(key).strip().upper()
            if phase_key not in config:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown phase in pairingConfig: {phase_key}",
                )
            config[phase_key] = _normalize_pairing_value(str(value))
    return config


def _normalize_pairing_mode(mode: str | None) -> str:
    if not mode:
        return "cross"
    return mode.strip().lower()


def _normalize_pairing_value(value: str | None) -> str:
    if not value:
        return "CROSS"
    normalized = value.strip().upper()
    if normalized in {"CROSS", "RANDOM", "MANUAL", "SEEDED"}:
        return normalized
    if normalized == "SEED":
        return "SEEDED"
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported pairing value: {value}",
    )


def _parse_seed_label(label: str) -> tuple[str, int]:
    match = re.match(r"^(.+?)\s*#\s*(\d+)$", label.strip())
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid seed label: {label}",
        )
    group_name = match.group(1).strip()
    rank = int(match.group(2))
    if rank <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid seed rank in label: {label}",
        )
    return group_name, rank


def _parse_seed_index(label: str) -> int:
    match = re.match(r"^(?:seed\s*)?#?\s*(\d+)$", label.strip(), flags=re.IGNORECASE)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid seed label: {label}",
        )
    seed = int(match.group(1))
    if seed <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid seed label: {label}",
        )
    return seed


def _load_team_league_map(db: Session, tournament_id: int, team_ids: list[int]) -> dict[int, set[int]]:
    if not team_ids:
        return {}
    rows = (
        db.query(LeagueTeamModel.teamId, LeagueTeamModel.leagueId)
        .join(LeagueModel, LeagueModel.id == LeagueTeamModel.leagueId)
        .filter(
            LeagueModel.tournamentId == tournament_id,
            LeagueTeamModel.teamId.in_(team_ids),
        )
        .all()
    )
    team_leagues: dict[int, set[int]] = {team_id: set() for team_id in team_ids}
    for team_id, league_id in rows:
        team_leagues.setdefault(team_id, set()).add(league_id)
    return team_leagues


def _resolve_match_league_id(
    team_leagues: dict[int, set[int]],
    team1_id: int,
    team2_id: int,
    requested_league_id: int | None,
) -> int:
    team1_leagues = team_leagues.get(team1_id, set())
    team2_leagues = team_leagues.get(team2_id, set())
    if requested_league_id is not None:
        if requested_league_id not in team1_leagues or requested_league_id not in team2_leagues:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Match teams do not belong to the selected league",
            )
        return requested_league_id

    common = team1_leagues.intersection(team2_leagues)
    if len(common) == 1:
        return next(iter(common))
    if len(common) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Match teams do not share a league. Provide leagueId.",
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Match teams share multiple leagues. Provide leagueId.",
    )


def _get_league_or_404(
    db: Session,
    tournament_id: int,
    league_id: int | None,
) -> LeagueModel | None:
    if league_id is None:
        return None
    league = (
        db.query(LeagueModel)
        .filter(
            LeagueModel.id == league_id,
            LeagueModel.tournamentId == tournament_id,
        )
        .first()
    )
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"League with ID {league_id} not found for this tournament",
        )
    return league


def _delete_group_matches(
    db: Session,
    group_ids: list[int],
    existing_matches: list[TournamentGroupMatchModel] | None = None,
) -> None:
    if not group_ids:
        return
    matches = existing_matches
    if matches is None:
        matches = (
            db.query(TournamentGroupMatchModel)
            .filter(TournamentGroupMatchModel.groupId.in_(group_ids))
            .all()
        )
    if not matches:
        return
    match_ids = [item.matchId for item in matches if item.matchId]
    db.query(TournamentGroupMatchModel).filter(
        TournamentGroupMatchModel.groupId.in_(group_ids)
    ).delete(synchronize_session=False)
    if match_ids:
        db.query(MatchModel).filter(MatchModel.id.in_(match_ids)).delete(synchronize_session=False)


def _delete_group_teams_and_groups(
    db: Session,
    tournament_id: int,
    group_ids: list[int],
) -> None:
    if not group_ids:
        return
    db.query(TournamentGroupTeamModel).filter(
        TournamentGroupTeamModel.groupId.in_(group_ids)
    ).delete(synchronize_session=False)
    db.query(TournamentGroupModel).filter(
        TournamentGroupModel.tournamentId == tournament_id
    ).delete(synchronize_session=False)


def _delete_knockout_matches(db: Session, tournament_id: int) -> None:
    existing = (
        db.query(TournamentKnockoutMatchModel)
        .filter(TournamentKnockoutMatchModel.tournamentId == tournament_id)
        .all()
    )
    if not existing:
        return
    match_ids = [item.matchId for item in existing if item.matchId]
    db.query(TournamentKnockoutMatchModel).filter(
        TournamentKnockoutMatchModel.tournamentId == tournament_id
    ).delete(synchronize_session=False)
    if match_ids:
        db.query(MatchModel).filter(MatchModel.id.in_(match_ids)).delete(synchronize_session=False)


def _ensure_groups_fully_assigned(
    tournament: TournamentModel,
    groups: list[TournamentGroupModel],
) -> None:
    if tournament.groupCount and tournament.teamsPerGroup:
        assigned_count = sum(len(group.teams or []) for group in groups)
        expected_count = tournament.groupCount * tournament.teamsPerGroup
        if assigned_count != expected_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Teams are not fully assigned to groups",
            )


def _collect_group_team_ids(groups: list[TournamentGroupModel]) -> list[int]:
    return [
        group_team.teamId
        for group in groups
        for group_team in (group.teams or [])
        if group_team.teamId
    ]


def _create_match(
    db: Session,
    *,
    team1_id: int,
    team2_id: int,
    timestamp: datetime,
    league_id: int,
    location: str | None = None,
    state: MatchState = MatchState.SCHEDULED,
) -> MatchModel:
    match = MatchModel(
        team1Id=team1_id,
        team2Id=team2_id,
        timestamp=timestamp,
        state=state,
        leagueId=league_id,
        location=location,
    )
    db.add(match)
    db.flush()
    # Keep attendance in sync with auto-generated matches.
    ensure_match_attendance_for_default_team(db, match)
    return match


def _create_group_match(
    db: Session,
    *,
    group_id: int,
    match_id: int,
    round_number: int,
    order: int,
) -> None:
    db.add(TournamentGroupMatchModel(
        groupId=group_id,
        matchId=match_id,
        round=round_number,
        order=order,
    ))


def _create_knockout_match(
    db: Session,
    *,
    tournament_id: int,
    match_id: int,
    round_label: str | None,
    order: int,
) -> None:
    db.add(TournamentKnockoutMatchModel(
        tournamentId=tournament_id,
        matchId=match_id,
        round=round_label,
        order=order,
    ))


def _ensure_unique_manual_pairs(manual_pairs: list) -> None:
    seen_slots = set()
    for pair in manual_pairs:
        for slot in (pair.home, pair.away):
            if slot in seen_slots:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="manualPairs contains duplicate slots",
                )
            seen_slots.add(slot)
