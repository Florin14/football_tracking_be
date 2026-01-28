import json
import math
import random
import re
from datetime import datetime, timedelta

from fastapi import Body, Depends, HTTPException, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload

from constants.match_state import MatchState
from extensions.sqlalchemy import get_db
from modules.match.models.match_model import MatchModel
from modules.team.models.team_model import TeamModel
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.league_team_model import LeagueTeamModel
from modules.tournament.models.tournament_group_match_model import TournamentGroupMatchModel
from modules.tournament.models.tournament_group_model import TournamentGroupModel
from modules.tournament.models.tournament_group_team_model import TournamentGroupTeamModel
from modules.tournament.models.tournament_knockout_match_model import TournamentKnockoutMatchModel
from modules.tournament.models.tournament_model import TournamentModel
from modules.tournament.models.tournament_schemas import (
    TournamentGroupsAutoAssignRequest,
    TournamentGroupMatchesResponse,
    TournamentGroupScheduleSimpleRequest,
    TournamentGroupScheduleRequest,
    TournamentGroupStandingsResponse,
    TournamentGroupStandingsItem,
    TournamentGroupMatchItem,
    TournamentKnockoutAutoRequest,
    TournamentKnockoutBulkCreateRequest,
    TournamentKnockoutConfig,
    TournamentKnockoutGenerateRequest,
    TournamentStructureResponse,
)
from modules.tournament.models.tournament_knockout_config_model import TournamentKnockoutConfigModel
from modules.attendance.services.attendance_service import ensure_match_attendance_for_default_team
from modules.tournament.routes.tournament_structure import (
    _validate_teams_belong_to_tournament,
    get_tournament_structure,
)
from .router import router

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
        if match.state != MatchState.FINISHED:
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
                func.sum(case((MatchModel.state == MatchState.FINISHED, 1), else_=0)),
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
        if not match or match.state != MatchState.FINISHED:
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
        if not match or match.state != MatchState.FINISHED:
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
    match = re.match(r"^(?:seed\\s*)?#?\\s*(\\d+)$", label.strip(), flags=re.IGNORECASE)
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


@router.post("/{tournament_id}/groups/auto", response_model=TournamentStructureResponse)
async def auto_assign_groups(
    tournament_id: int,
    data: TournamentGroupsAutoAssignRequest,
    db: Session = Depends(get_db),
):
    tournament = _get_tournament_or_404(db, tournament_id)
    teams = _get_tournament_teams(db, tournament_id)
    if not teams:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No teams found for this tournament",
        )

    group_count = data.groupCount or tournament.groupCount
    teams_per_group = data.teamsPerGroup or tournament.teamsPerGroup
    if not group_count and not teams_per_group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="groupCount or teamsPerGroup is required",
        )

    if not group_count:
        group_count = max(1, math.ceil(len(teams) / teams_per_group))
    if not teams_per_group:
        teams_per_group = max(1, math.ceil(len(teams) / group_count))
    if group_count > len(teams):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="groupCount cannot exceed number of teams",
        )

    existing_groups = (
        db.query(TournamentGroupModel)
        .filter(TournamentGroupModel.tournamentId == tournament_id)
        .all()
    )
    if existing_groups and not data.replaceExisting:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Groups already exist for this tournament",
        )
    if existing_groups and data.replaceExisting:
        group_ids = [group.id for group in existing_groups]
        if group_ids:
            existing_matches = (
                db.query(TournamentGroupMatchModel)
                .filter(TournamentGroupMatchModel.groupId.in_(group_ids))
                .all()
            )
            match_ids = [item.matchId for item in existing_matches]
            db.query(TournamentGroupMatchModel).filter(
                TournamentGroupMatchModel.groupId.in_(group_ids)
            ).delete(synchronize_session=False)
            if match_ids:
                db.query(MatchModel).filter(MatchModel.id.in_(match_ids)).delete(synchronize_session=False)
            db.query(TournamentGroupTeamModel).filter(
                TournamentGroupTeamModel.groupId.in_(group_ids)
            ).delete(synchronize_session=False)
        db.query(TournamentGroupModel).filter(
            TournamentGroupModel.tournamentId == tournament_id
        ).delete(synchronize_session=False)

    groups = []
    for index in range(group_count):
        group = TournamentGroupModel(
            name=_build_group_name(index),
            order=index + 1,
            tournamentId=tournament_id,
        )
        db.add(group)
        groups.append(group)
    db.flush()

    teams_list = list(teams)
    if data.shuffleTeams:
        random.shuffle(teams_list)

    for idx, team in enumerate(teams_list):
        group = groups[idx % group_count]
        db.add(TournamentGroupTeamModel(groupId=group.id, teamId=team.id))

    db.commit()
    return await get_tournament_structure(tournament_id, db)


@router.post("/{tournament_id}/groups/schedule", response_model=TournamentStructureResponse)
async def generate_group_schedule(
    tournament_id: int,
    data: TournamentGroupScheduleRequest,
    db: Session = Depends(get_db),
):
    tournament = _get_tournament_or_404(db, tournament_id)
    groups = _load_groups_with_teams(db, tournament_id)
    if not groups:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No groups found for this tournament",
        )
    if tournament.groupCount and tournament.teamsPerGroup:
        assigned_count = sum(len(group.teams or []) for group in groups)
        expected_count = tournament.groupCount * tournament.teamsPerGroup
        if assigned_count != expected_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Teams are not fully assigned to groups",
            )
    if tournament.groupCount and tournament.teamsPerGroup:
        assigned_count = sum(len(group.teams or []) for group in groups)
        expected_count = tournament.groupCount * tournament.teamsPerGroup
        if assigned_count != expected_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Teams are not fully assigned to groups",
            )

    group_ids = [group.id for group in groups]
    existing_matches = (
        db.query(TournamentGroupMatchModel)
        .filter(TournamentGroupMatchModel.groupId.in_(group_ids))
        .all()
    )
    if existing_matches and not data.replaceExisting:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Group matches already exist for this tournament",
        )
    if existing_matches and data.replaceExisting:
        match_ids = [item.matchId for item in existing_matches]
        db.query(TournamentGroupMatchModel).filter(
            TournamentGroupMatchModel.groupId.in_(group_ids)
        ).delete(synchronize_session=False)
        if match_ids:
            db.query(MatchModel).filter(MatchModel.id.in_(match_ids)).delete(synchronize_session=False)

    team_ids_all = [gt.teamId for group in groups for gt in (group.teams or []) if gt.teamId]
    team_leagues = _load_team_league_map(db, tournament_id, team_ids_all)

    if data.leagueId is not None:
        league = (
            db.query(LeagueModel)
            .filter(LeagueModel.id == data.leagueId, LeagueModel.tournamentId == tournament_id)
            .first()
        )
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"League with ID {data.leagueId} not found for this tournament",
            )

    match_specs = []
    for group in groups:
        team_ids = [gt.teamId for gt in group.teams if gt.teamId]
        if len(team_ids) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Group {group.name} needs at least 2 teams to schedule matches",
            )
        rounds = _generate_round_robin(team_ids, data.randomize)
        for round_index, pairs in enumerate(rounds, start=1):
            for team1_id, team2_id in pairs:
                league_id = _resolve_match_league_id(
                    team_leagues,
                    team1_id,
                    team2_id,
                    data.leagueId,
                )
                match_specs.append({
                    "groupId": group.id,
                    "round": round_index,
                    "team1Id": team1_id,
                    "team2Id": team2_id,
                    "leagueId": league_id,
                })

    ordered_specs = _order_matches(match_specs, data.avoidConsecutive)
    interval = timedelta(minutes=data.intervalMinutes)

    created_matches = []
    for index, spec in enumerate(ordered_specs, start=1):
        match = MatchModel(
            team1Id=spec["team1Id"],
            team2Id=spec["team2Id"],
            timestamp=data.startTimestamp + interval * (index - 1),
            state=MatchState.SCHEDULED,
            leagueId=spec["leagueId"],
        )
        db.add(match)
        db.flush()
        db.add(TournamentGroupMatchModel(
            groupId=spec["groupId"],
            matchId=match.id,
            round=spec["round"],
            order=index,
        ))
        ensure_match_attendance_for_default_team(db, match)
        created_matches.append(match)

    db.commit()

    return await get_tournament_structure(tournament_id, db)


@router.post("/{tournament_id}/groups/schedule/reset", response_model=TournamentStructureResponse)
async def reset_group_schedule(
    tournament_id: int,
    db: Session = Depends(get_db),
):
    _get_tournament_or_404(db, tournament_id)
    group_ids = [
        group.id
        for group in db.query(TournamentGroupModel.id)
        .filter(TournamentGroupModel.tournamentId == tournament_id)
        .all()
    ]
    if group_ids:
        existing_matches = (
            db.query(TournamentGroupMatchModel)
            .filter(TournamentGroupMatchModel.groupId.in_(group_ids))
            .all()
        )
        match_ids = [item.matchId for item in existing_matches]
        db.query(TournamentGroupMatchModel).filter(
            TournamentGroupMatchModel.groupId.in_(group_ids)
        ).delete(synchronize_session=False)
        if match_ids:
            db.query(MatchModel).filter(MatchModel.id.in_(match_ids)).delete(synchronize_session=False)

    db.commit()
    return await get_tournament_structure(tournament_id, db)


@router.delete("/{tournament_id}/group-schedule", response_model=TournamentStructureResponse)
async def delete_group_schedule(
    tournament_id: int,
    db: Session = Depends(get_db),
):
    return await reset_group_schedule(tournament_id, db)


@router.post("/{tournament_id}/group-schedule", response_model=TournamentStructureResponse)
async def generate_group_schedule_simple(
    tournament_id: int,
    data: TournamentGroupScheduleSimpleRequest,
    db: Session = Depends(get_db),
):
    mode = (data.mode or "round-robin").strip().lower()
    mode = mode.replace("_", "-").replace(" ", "-")
    if mode not in {"round-robin", "roundrobin"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only round-robin mode is supported",
        )

    payload = TournamentGroupScheduleRequest(
        startTimestamp=data.startTimestamp or datetime.utcnow(),
        intervalMinutes=data.intervalMinutes,
        randomize=data.randomize,
        avoidConsecutive=data.avoidConsecutive,
        replaceExisting=data.replaceExisting,
        leagueId=data.leagueId,
    )
    return await generate_group_schedule(tournament_id, payload, db)


@router.get("/{tournament_id}/groups/matches", response_model=TournamentGroupMatchesResponse)
async def get_group_matches(tournament_id: int, db: Session = Depends(get_db)):
    _get_tournament_or_404(db, tournament_id)
    groups = _load_groups_with_teams(db, tournament_id)
    group_ids = [group.id for group in groups]
    if not group_ids:
        return TournamentGroupMatchesResponse(groups=[], matches=[])

    matches = (
        db.query(TournamentGroupMatchModel)
        .options(joinedload(TournamentGroupMatchModel.match))
        .filter(TournamentGroupMatchModel.groupId.in_(group_ids))
        .order_by(
            TournamentGroupMatchModel.order.is_(None),
            TournamentGroupMatchModel.order,
            TournamentGroupMatchModel.id,
        )
        .all()
    )

    match_items = []
    for item in matches:
        match = item.match
        if not match:
            continue
        match_items.append(TournamentGroupMatchItem(
            id=item.id,
            groupId=item.groupId,
            matchId=match.id,
            round=item.round,
            order=item.order,
            team1Id=match.team1Id,
            team2Id=match.team2Id,
            scoreTeam1=match.scoreTeam1,
            scoreTeam2=match.scoreTeam2,
            state=match.state.value if hasattr(match.state, "value") else str(match.state),
            timestamp=match.timestamp,
        ))

    return TournamentGroupMatchesResponse(
        groups=[{
            "id": group.id,
            "name": group.name,
            "order": group.order,
            "teams": [
                {
                    "id": gt.team.id,
                    "name": gt.team.name,
                    "description": gt.team.description,
                    "logo": gt.team.logo,
                    "playerCount": 0,
                }
                for gt in group.teams
                if gt.team
            ],
        } for group in groups],
        matches=match_items,
    )


@router.get("/{tournament_id}/groups/standings", response_model=TournamentGroupStandingsResponse)
async def get_group_standings(tournament_id: int, db: Session = Depends(get_db)):
    _get_tournament_or_404(db, tournament_id)
    groups = _load_groups_with_teams(db, tournament_id)
    if not groups:
        return TournamentGroupStandingsResponse(groups=[])

    group_ids = [group.id for group in groups]
    group_matches = (
        db.query(TournamentGroupMatchModel)
        .options(joinedload(TournamentGroupMatchModel.match))
        .filter(TournamentGroupMatchModel.groupId.in_(group_ids))
        .all()
    )
    matches_by_group: dict[int, list[MatchModel]] = {}
    for item in group_matches:
        if not item.match:
            continue
        matches_by_group.setdefault(item.groupId, []).append(item.match)

    group_items = []
    for group in groups:
        standings = _build_group_standings(group, matches_by_group.get(group.id, []))
        group_items.append(TournamentGroupStandingsItem(
            groupId=group.id,
            groupName=group.name,
            teams=standings,
        ))

    return TournamentGroupStandingsResponse(groups=group_items)


@router.post("/{tournament_id}/knockout-matches/bulk", response_model=TournamentStructureResponse)
async def create_knockout_matches_bulk(
    tournament_id: int,
    data: TournamentKnockoutBulkCreateRequest,
    db: Session = Depends(get_db),
):
    _get_tournament_or_404(db, tournament_id)
    team_ids = [team_id for entry in data.matches for team_id in (entry.team1Id, entry.team2Id)]
    team_leagues = _load_team_league_map(db, tournament_id, team_ids)

    if data.replaceExisting:
        existing = (
            db.query(TournamentKnockoutMatchModel)
            .filter(TournamentKnockoutMatchModel.tournamentId == tournament_id)
            .all()
        )
        match_ids = [item.matchId for item in existing]
        db.query(TournamentKnockoutMatchModel).filter(
            TournamentKnockoutMatchModel.tournamentId == tournament_id
        ).delete(synchronize_session=False)
        if match_ids:
            db.query(MatchModel).filter(MatchModel.id.in_(match_ids)).delete(synchronize_session=False)

    for entry in data.matches:
        _validate_teams_belong_to_tournament(db, tournament_id, [entry.team1Id, entry.team2Id])
        league_id = _resolve_match_league_id(team_leagues, entry.team1Id, entry.team2Id, None)
        match = MatchModel(
            team1Id=entry.team1Id,
            team2Id=entry.team2Id,
            location=entry.location,
            timestamp=entry.timestamp,
            state=MatchState.SCHEDULED,
            leagueId=league_id,
        )
        db.add(match)
        db.flush()
        db.add(TournamentKnockoutMatchModel(
            tournamentId=tournament_id,
            matchId=match.id,
            round=entry.round,
            order=entry.order,
        ))
        ensure_match_attendance_for_default_team(db, match)

    db.commit()
    return await get_tournament_structure(tournament_id, db)


@router.post("/{tournament_id}/knockout-matches/auto", response_model=TournamentStructureResponse)
async def create_knockout_matches_auto(
    tournament_id: int,
    data: TournamentKnockoutAutoRequest,
    db: Session = Depends(get_db),
):
    _get_tournament_or_404(db, tournament_id)
    groups = _load_groups_with_teams(db, tournament_id)
    if not groups:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No groups found for this tournament",
        )

    standings_response = await get_group_standings(tournament_id, db)
    standings_by_group = {item.groupId: item.teams for item in standings_response.groups}
    ordered_groups = sorted(groups, key=lambda g: (g.order is None, g.order or 0, g.name.lower()))
    group_completion = _get_group_completion_map(db, [group.id for group in ordered_groups])

    if data.pairingStrategy not in {"cross", "seeded", "random"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pairingStrategy must be 'cross', 'seeded' or 'random'",
        )

    if data.pairingStrategy in {"seeded", "random"}:
        incomplete_groups = [group.name for group in ordered_groups if not group_completion.get(group.id)]
        if incomplete_groups:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot generate knockout matches until all groups are finished",
            )

    pairs_with_order: list[tuple[int, int, int]] = []
    order_index = 1
    total_possible_matches = 0
    if data.pairingStrategy == "cross":
        if len(ordered_groups) % 2 != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cross pairing requires an even number of groups",
            )
        if data.qualifiersPerGroup > 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cross pairing supports up to 2 qualifiers per group",
            )
        for i in range(0, len(ordered_groups), 2):
            group_a = ordered_groups[i]
            group_b = ordered_groups[i + 1]
            group_a_ready = group_completion.get(group_a.id, False)
            group_b_ready = group_completion.get(group_b.id, False)
            if not (group_a_ready and group_b_ready):
                order_index += 1 if data.qualifiersPerGroup == 1 else 2
                continue
            group_a_standings = standings_by_group.get(group_a.id, [])
            group_b_standings = standings_by_group.get(group_b.id, [])
            if len(group_a_standings) < data.qualifiersPerGroup or len(group_b_standings) < data.qualifiersPerGroup:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Not enough teams to qualify {data.qualifiersPerGroup} team(s) for {group_a.name}/{group_b.name}",
                )
            if data.qualifiersPerGroup == 1:
                pairs_with_order.append((order_index, group_a_standings[0].id, group_b_standings[0].id))
                order_index += 1
            else:
                pairs_with_order.append((order_index, group_a_standings[0].id, group_b_standings[1].id))
                order_index += 1
                pairs_with_order.append((order_index, group_b_standings[0].id, group_a_standings[1].id))
                order_index += 1
    else:
        qualifiers = []
        for group in ordered_groups:
            group_standings = standings_by_group.get(group.id, [])
            if len(group_standings) < data.qualifiersPerGroup:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Not enough teams to qualify {data.qualifiersPerGroup} team(s) for {group.name}",
                )
            qualifiers.append(group_standings[: data.qualifiersPerGroup])

        pairs: list[tuple[int, int]] = []
        if data.pairingStrategy == "seeded":
            flat = []
            for group in qualifiers:
                flat.extend(group)
            ordered = [team.id for team in flat]
            while len(ordered) >= 2:
                pairs.append((ordered.pop(0), ordered.pop(-1)))
        else:
            flat = []
            for group in qualifiers:
                flat.extend(group)
            ordered = [team.id for team in flat]
            random.shuffle(ordered)
            while len(ordered) >= 2:
                pairs.append((ordered.pop(0), ordered.pop(0)))

        for team1_id, team2_id in pairs:
            pairs_with_order.append((order_index, team1_id, team2_id))
            order_index += 1

    team_ids_all = [team_id for _, team_id, _ in pairs_with_order] + [team_id for _, _, team_id in pairs_with_order]
    team_leagues = _load_team_league_map(db, tournament_id, team_ids_all)
    if data.leagueId is not None:
        league = (
            db.query(LeagueModel)
            .filter(LeagueModel.id == data.leagueId, LeagueModel.tournamentId == tournament_id)
            .first()
        )
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"League with ID {data.leagueId} not found for this tournament",
            )

    if data.replaceExisting:
        existing = (
            db.query(TournamentKnockoutMatchModel)
            .filter(TournamentKnockoutMatchModel.tournamentId == tournament_id)
            .all()
        )
        match_ids = [item.matchId for item in existing]
        db.query(TournamentKnockoutMatchModel).filter(
            TournamentKnockoutMatchModel.tournamentId == tournament_id
        ).delete(synchronize_session=False)
        if match_ids:
            db.query(MatchModel).filter(MatchModel.id.in_(match_ids)).delete(synchronize_session=False)

    round_label = data.round
    existing_orders = set()
    if not data.replaceExisting:
        existing_query = db.query(TournamentKnockoutMatchModel.order).filter(
            TournamentKnockoutMatchModel.tournamentId == tournament_id
        )
        if round_label is None:
            existing_query = existing_query.filter(TournamentKnockoutMatchModel.round.is_(None))
        else:
            existing_query = existing_query.filter(TournamentKnockoutMatchModel.round == round_label)
        existing_orders = {row[0] for row in existing_query.all()}

    interval = timedelta(minutes=data.intervalMinutes)
    for order, team1_id, team2_id in pairs_with_order:
        if order in existing_orders:
            continue
        league_id = _resolve_match_league_id(team_leagues, team1_id, team2_id, data.leagueId)
        match = MatchModel(
            team1Id=team1_id,
            team2Id=team2_id,
            timestamp=data.startTimestamp + interval * (order - 1),
            state=MatchState.SCHEDULED,
            leagueId=league_id,
        )
        db.add(match)
        db.flush()
        db.add(TournamentKnockoutMatchModel(
            tournamentId=tournament_id,
            matchId=match.id,
            round=round_label,
            order=order,
        ))
        ensure_match_attendance_for_default_team(db, match)

    db.commit()
    return await get_tournament_structure(tournament_id, db)


@router.post("/{tournament_id}/knockout-config", response_model=TournamentKnockoutConfig)
async def set_knockout_config(
    tournament_id: int,
    data: TournamentKnockoutConfig,
    db: Session = Depends(get_db),
):
    _get_tournament_or_404(db, tournament_id)
    pairing_mode = _normalize_pairing_mode(data.pairingMode)
    if pairing_mode not in {"cross", "random", "manual", "seeded"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pairingMode must be 'CROSS', 'RANDOM', 'SEEDED' or 'MANUAL'",
        )

    manual_pairs = data.manualPairs or []
    manual_pairs_by_phase = data.manualPairsByPhase or None
    if pairing_mode == "manual":
        if not manual_pairs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="manualPairs is required when pairingMode is MANUAL",
            )
        seen_slots = set()
        for pair in manual_pairs:
            for slot in [pair.home, pair.away]:
                if slot in seen_slots:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="manualPairs contains duplicate slots",
                    )
                seen_slots.add(slot)

    config = (
        db.query(TournamentKnockoutConfigModel)
        .filter(TournamentKnockoutConfigModel.tournamentId == tournament_id)
        .first()
    )
    payload = TournamentKnockoutConfigModel(
        tournamentId=tournament_id,
        qualifiersPerGroup=data.qualifiersPerGroup,
        pairingMode=pairing_mode,
        manualPairs=json.dumps([pair.model_dump() for pair in manual_pairs]) if manual_pairs else None,
        pairingConfig=json.dumps(data.pairingConfig) if data.pairingConfig else None,
        manualPairsByPhase=(
            json.dumps({
                phase: [pair.model_dump() for pair in pairs]
                for phase, pairs in manual_pairs_by_phase.items()
            })
            if manual_pairs_by_phase
            else None
        ),
    )
    if config:
        config.qualifiersPerGroup = payload.qualifiersPerGroup
        config.pairingMode = payload.pairingMode
        config.manualPairs = payload.manualPairs
        config.pairingConfig = payload.pairingConfig
        config.manualPairsByPhase = payload.manualPairsByPhase
    else:
        db.add(payload)
    db.commit()

    return TournamentKnockoutConfig(
        qualifiersPerGroup=payload.qualifiersPerGroup,
        pairingMode=payload.pairingMode,
        manualPairs=manual_pairs,
        pairingConfig=data.pairingConfig,
        manualPairsByPhase=manual_pairs_by_phase,
    )


@router.post("/{tournament_id}/knockout-generate", response_model=TournamentStructureResponse)
async def generate_knockout_matches_from_config(
    tournament_id: int,
    data: TournamentKnockoutGenerateRequest = Body(default_factory=TournamentKnockoutGenerateRequest),
    db: Session = Depends(get_db),
):
    tournament = _get_tournament_or_404(db, tournament_id)
    config = (
        db.query(TournamentKnockoutConfigModel)
        .filter(TournamentKnockoutConfigModel.tournamentId == tournament_id)
        .first()
    )
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knockout config not found",
        )

    qualifiers_per_group = config.qualifiersPerGroup
    if qualifiers_per_group is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="qualifiersPerGroup is required in knockout config",
        )
    if tournament.teamsPerGroup and qualifiers_per_group > tournament.teamsPerGroup:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="qualifiersPerGroup cannot exceed teamsPerGroup",
        )

    groups = _load_groups_with_teams(db, tournament_id)
    if not groups:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No groups found for this tournament",
        )

    pairing_config_raw = None
    if config.pairingConfig:
        try:
            pairing_config_raw = json.loads(config.pairingConfig)
        except json.JSONDecodeError:
            pairing_config_raw = None
    pairing_config = _normalize_pairing_config(pairing_config_raw, config.pairingMode)

    manual_pairs_by_phase = None
    if config.manualPairsByPhase:
        try:
            manual_pairs_by_phase = json.loads(config.manualPairsByPhase)
        except json.JSONDecodeError:
            manual_pairs_by_phase = None

    standings_response = await get_group_standings(tournament_id, db)
    standings_by_group = {item.groupId: item.teams for item in standings_response.groups}
    ordered_groups = sorted(groups, key=lambda g: (g.order is None, g.order or 0, g.name.lower()))
    group_completion = _get_group_completion_map(db, [group.id for group in ordered_groups])

    if data.leagueId is not None:
        league = (
            db.query(LeagueModel)
            .filter(LeagueModel.id == data.leagueId, LeagueModel.tournamentId == tournament_id)
            .first()
        )
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"League with ID {data.leagueId} not found for this tournament",
            )

    if data.replaceExisting:
        existing = (
            db.query(TournamentKnockoutMatchModel)
            .filter(TournamentKnockoutMatchModel.tournamentId == tournament_id)
            .all()
        )
        match_ids = [item.matchId for item in existing]
        db.query(TournamentKnockoutMatchModel).filter(
            TournamentKnockoutMatchModel.tournamentId == tournament_id
        ).delete(synchronize_session=False)
        if match_ids:
            db.query(MatchModel).filter(MatchModel.id.in_(match_ids)).delete(synchronize_session=False)

    total_qualifiers = len(ordered_groups) * qualifiers_per_group
    if total_qualifiers not in {2, 4, 8, 16}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Qualifiers count must be 2, 4, 8, or 16 to generate knockout phases",
        )

    initial_phase = {16: "RO16", 8: "QF", 4: "SF", 2: "F"}[total_qualifiers]
    initial_pairing = pairing_config.get(initial_phase, "CROSS")
    if manual_pairs_by_phase is None and config.manualPairs:
        try:
            legacy_pairs = json.loads(config.manualPairs)
        except json.JSONDecodeError:
            legacy_pairs = []
        manual_pairs_by_phase = {initial_phase: legacy_pairs} if legacy_pairs else None

    def create_matches_for_phase(
        phase: str,
        participants: list[int],
        pairing_value: str,
        start_time: datetime,
        interval: timedelta,
    ) -> None:
        if not participants or len(participants) < 2:
            return
        pairs: list[tuple[int, int]] = []
        if len(participants) == 2:
            pairs.append((participants[0], participants[1]))
        elif pairing_value == "RANDOM":
            ordered = list(participants)
            random.shuffle(ordered)
            while len(ordered) >= 2:
                pairs.append((ordered.pop(0), ordered.pop(0)))
        elif pairing_value in {"SEEDED", "CROSS"}:
            ordered = list(participants)
            while len(ordered) >= 2:
                pairs.append((ordered.pop(0), ordered.pop(-1)))
        elif pairing_value == "MANUAL":
            phase_pairs = (manual_pairs_by_phase or {}).get(phase) or []
            if not phase_pairs:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"manualPairs are required for phase {phase}. Provide manualPairsByPhase['{phase}']",
                )
            for pair in phase_pairs:
                home_index = _parse_seed_index(pair["home"])
                away_index = _parse_seed_index(pair["away"])
                if home_index > len(participants) or away_index > len(participants):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"manualPairs seed index out of range for phase {phase}",
                    )
                pairs.append((participants[home_index - 1], participants[away_index - 1]))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported pairing mode for phase {phase}",
            )

        existing_orders = {
            row[0]
            for row in db.query(TournamentKnockoutMatchModel.order)
            .filter(
                TournamentKnockoutMatchModel.tournamentId == tournament_id,
                TournamentKnockoutMatchModel.round == phase,
            )
            .all()
        }
        team_leagues = _load_team_league_map(
            db, tournament_id, [team_id for pair in pairs for team_id in pair]
        )
        for idx, (team1_id, team2_id) in enumerate(pairs, start=1):
            if idx in existing_orders:
                continue
            league_id = _resolve_match_league_id(team_leagues, team1_id, team2_id, data.leagueId)
            match = MatchModel(
                team1Id=team1_id,
                team2Id=team2_id,
                timestamp=start_time + interval * (idx - 1),
                state=MatchState.SCHEDULED,
                leagueId=league_id,
            )
            db.add(match)
            db.flush()
            db.add(TournamentKnockoutMatchModel(
                tournamentId=tournament_id,
                matchId=match.id,
                round=phase,
                order=idx,
            ))
            ensure_match_attendance_for_default_team(db, match)

    def build_initial_participants() -> list[tuple[int, int, int]]:
        pairs_with_order: list[tuple[int, int, int]] = []
        order_index = 1
        if initial_pairing == "CROSS":
            if len(ordered_groups) % 2 != 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cross pairing requires an even number of groups",
                )
            if qualifiers_per_group > 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cross pairing supports up to 2 qualifiers per group",
                )
            for i in range(0, len(ordered_groups), 2):
                group_a = ordered_groups[i]
                group_b = ordered_groups[i + 1]
                group_a_ready = group_completion.get(group_a.id, False)
                group_b_ready = group_completion.get(group_b.id, False)
                if not (group_a_ready and group_b_ready):
                    order_index += 1 if qualifiers_per_group == 1 else 2
                    continue
                group_a_standings = standings_by_group.get(group_a.id, [])
                group_b_standings = standings_by_group.get(group_b.id, [])
                if len(group_a_standings) < qualifiers_per_group or len(group_b_standings) < qualifiers_per_group:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Not enough teams to qualify {qualifiers_per_group} team(s) for {group_a.name}/{group_b.name}",
                    )
                if qualifiers_per_group == 1:
                    pairs_with_order.append((order_index, group_a_standings[0].id, group_b_standings[0].id))
                    order_index += 1
                else:
                    pairs_with_order.append((order_index, group_a_standings[0].id, group_b_standings[1].id))
                    order_index += 1
                    pairs_with_order.append((order_index, group_b_standings[0].id, group_a_standings[1].id))
                    order_index += 1
        elif initial_pairing in {"RANDOM", "SEEDED"}:
            incomplete_groups = [group.name for group in ordered_groups if not group_completion.get(group.id)]
            if incomplete_groups:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot generate knockout matches until all groups are finished",
                )
            qualifiers = []
            for group in ordered_groups:
                group_standings = standings_by_group.get(group.id, [])
                if len(group_standings) < qualifiers_per_group:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Not enough teams to qualify {qualifiers_per_group} team(s) for {group.name}",
                    )
                qualifiers.append(group_standings[: qualifiers_per_group])
            flat = []
            for group in qualifiers:
                flat.extend(group)
            ordered = [team.id for team in flat]
            if initial_pairing == "RANDOM":
                random.shuffle(ordered)
            pairs: list[tuple[int, int]] = []
            if initial_pairing == "SEEDED":
                while len(ordered) >= 2:
                    pairs.append((ordered.pop(0), ordered.pop(-1)))
            else:
                while len(ordered) >= 2:
                    pairs.append((ordered.pop(0), ordered.pop(0)))
            for team1_id, team2_id in pairs:
                pairs_with_order.append((order_index, team1_id, team2_id))
                order_index += 1
        elif initial_pairing == "MANUAL":
            manual_pairs = (manual_pairs_by_phase or {}).get(initial_phase) or []
            if not manual_pairs:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"manualPairs are required for phase {initial_phase}",
                )
            group_by_name = {group.name.lower(): group for group in ordered_groups}
            for pair in manual_pairs:
                group_name, rank = _parse_seed_label(pair["home"])
                group = group_by_name.get(group_name.lower())
                if not group:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Unknown group in label: {pair['home']}",
                    )
                if not group_completion.get(group.id, False):
                    order_index += 1
                    continue
                group_standings = standings_by_group.get(group.id, [])
                if len(group_standings) < rank:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Not enough teams in group for label: {pair['home']}",
                    )
                home_team = group_standings[rank - 1].id
                group_name, rank = _parse_seed_label(pair["away"])
                group = group_by_name.get(group_name.lower())
                if not group:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Unknown group in label: {pair['away']}",
                    )
                if not group_completion.get(group.id, False):
                    order_index += 1
                    continue
                group_standings = standings_by_group.get(group.id, [])
                if len(group_standings) < rank:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Not enough teams in group for label: {pair['away']}",
                    )
                away_team = group_standings[rank - 1].id
                pairs_with_order.append((order_index, home_team, away_team))
                order_index += 1
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported pairing mode for phase {initial_phase}",
            )
        return pairs_with_order

    start_time = data.startTimestamp or datetime.utcnow()
    interval = timedelta(minutes=data.intervalMinutes)

    pairs_with_order = build_initial_participants()
    if pairs_with_order:
        team_leagues = _load_team_league_map(
            db,
            tournament_id,
            [team_id for _, team_id, _ in pairs_with_order] + [team_id for _, _, team_id in pairs_with_order],
        )
        existing_orders = {
            row[0]
            for row in db.query(TournamentKnockoutMatchModel.order)
            .filter(
                TournamentKnockoutMatchModel.tournamentId == tournament_id,
                TournamentKnockoutMatchModel.round == initial_phase,
            )
            .all()
        }
        for order, team1_id, team2_id in pairs_with_order:
            if order in existing_orders:
                continue
            league_id = _resolve_match_league_id(team_leagues, team1_id, team2_id, data.leagueId)
            match = MatchModel(
                team1Id=team1_id,
                team2Id=team2_id,
                timestamp=start_time + interval * (order - 1),
                state=MatchState.SCHEDULED,
                leagueId=league_id,
            )
            db.add(match)
            db.flush()
            db.add(TournamentKnockoutMatchModel(
                tournamentId=tournament_id,
                matchId=match.id,
                round=initial_phase,
                order=order,
            ))
            ensure_match_attendance_for_default_team(db, match)

    phase_chain = {
        "RO16": "QF",
        "QF": "SF",
        "SF": "F",
    }
    current_phase = initial_phase
    while current_phase in phase_chain:
        next_phase = phase_chain[current_phase]
        current_entries = _load_knockout_entries(db, tournament_id, current_phase)
        if not current_entries:
            break
        winners = _get_knockout_winners(current_entries)
        if any(winner is None for winner in winners):
            break
        participants = [winner for winner in winners if winner is not None]
        next_pairing = pairing_config.get(next_phase, "CROSS")
        create_matches_for_phase(next_phase, participants, next_pairing, start_time, interval)
        current_phase = next_phase

    sf_entries = _load_knockout_entries(db, tournament_id, "SF")
    if sf_entries:
        sf_losers = _get_knockout_losers(sf_entries)
        if sf_losers and not any(loser is None for loser in sf_losers):
            participants = [loser for loser in sf_losers if loser is not None]
            third_place_pairing = pairing_config.get("3P", "CROSS")
            create_matches_for_phase("3P", participants, third_place_pairing, start_time, interval)

    db.commit()
    return await get_tournament_structure(tournament_id, db)
