import math
import random
from datetime import timedelta

from fastapi import Depends, HTTPException, status
from sqlalchemy import func
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
    TournamentGroupScheduleRequest,
    TournamentGroupStandingsResponse,
    TournamentGroupStandingsItem,
    TournamentGroupMatchItem,
    TournamentKnockoutAutoRequest,
    TournamentKnockoutBulkCreateRequest,
    TournamentStructureResponse,
)
from modules.tournament.routes.tournament_structure import (
    _validate_teams_belong_to_tournament,
    get_tournament_structure,
)
from .router import router


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
            db.query(TournamentGroupMatchModel).filter(
                TournamentGroupMatchModel.groupId.in_(group_ids)
            ).delete(synchronize_session=False)
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
    _get_tournament_or_404(db, tournament_id)
    groups = _load_groups_with_teams(db, tournament_id)
    if not groups:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No groups found for this tournament",
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
                match_specs.append({
                    "groupId": group.id,
                    "round": round_index,
                    "team1Id": team1_id,
                    "team2Id": team2_id,
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
        )
        db.add(match)
        db.flush()
        db.add(TournamentGroupMatchModel(
            groupId=spec["groupId"],
            matchId=match.id,
            round=spec["round"],
            order=index,
        ))
        created_matches.append(match)

    db.commit()

    return await get_tournament_structure(tournament_id, db)


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
        match = MatchModel(
            team1Id=entry.team1Id,
            team2Id=entry.team2Id,
            location=entry.location,
            timestamp=entry.timestamp,
            state=MatchState.SCHEDULED,
        )
        db.add(match)
        db.flush()
        db.add(TournamentKnockoutMatchModel(
            tournamentId=tournament_id,
            matchId=match.id,
            round=entry.round,
            order=entry.order,
        ))

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
    qualifiers = []
    for group in ordered_groups:
        group_standings = standings_by_group.get(group.id, [])
        if len(group_standings) < data.qualifiersPerGroup:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough teams to qualify {data.qualifiersPerGroup} team(s) for {group.name}",
            )
        qualifiers.append(group_standings[: data.qualifiersPerGroup])

    if data.pairingStrategy not in {"cross", "seeded"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pairingStrategy must be 'cross' or 'seeded'",
        )

    pairs: list[tuple[int, int]] = []
    if data.pairingStrategy == "cross":
        if len(qualifiers) % 2 != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cross pairing requires an even number of groups",
            )
        if data.qualifiersPerGroup > 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cross pairing supports up to 2 qualifiers per group",
            )
        for i in range(0, len(qualifiers), 2):
            group_a = qualifiers[i]
            group_b = qualifiers[i + 1]
            if data.qualifiersPerGroup == 1:
                pairs.append((group_a[0]["id"], group_b[0]["id"]))
            else:
                pairs.append((group_a[0]["id"], group_b[1]["id"]))
                pairs.append((group_b[0]["id"], group_a[1]["id"]))
    else:
        flat = []
        for group in qualifiers:
            flat.extend(group)
        ordered = [team["id"] for team in flat]
        while len(ordered) >= 2:
            pairs.append((ordered.pop(0), ordered.pop(-1)))

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

    interval = timedelta(minutes=data.intervalMinutes)
    for index, (team1_id, team2_id) in enumerate(pairs, start=1):
        match = MatchModel(
            team1Id=team1_id,
            team2Id=team2_id,
            timestamp=data.startTimestamp + interval * (index - 1),
            state=MatchState.SCHEDULED,
        )
        db.add(match)
        db.flush()
        db.add(TournamentKnockoutMatchModel(
            tournamentId=tournament_id,
            matchId=match.id,
            round=data.round,
            order=index,
        ))

    db.commit()
    return await get_tournament_structure(tournament_id, db)
