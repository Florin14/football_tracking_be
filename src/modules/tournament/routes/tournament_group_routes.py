import math
import random
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from project_helpers.dependencies import JwtRequired
from modules.match.models.match_model import MatchModel
from modules.tournament.models.tournament_group_match_model import TournamentGroupMatchModel
from modules.tournament.models.tournament_group_model import TournamentGroupModel
from modules.tournament.models.tournament_group_team_model import TournamentGroupTeamModel
from modules.tournament.models.tournament_schemas import (
    TournamentGroupMatchesResponse,
    TournamentGroupMatchItem,
    TournamentGroupScheduleRequest,
    TournamentGroupScheduleSimpleRequest,
    TournamentGroupStandingsItem,
    TournamentGroupStandingsResponse,
    TournamentGroupsAutoAssignRequest,
    TournamentStructureResponse,
)
from modules.tournament.routes.tournament_structure import get_tournament_structure

from .router import router
from .tournament_group_scheduling_helpers import (
    _build_group_name,
    _build_group_standings,
    _collect_group_team_ids,
    _create_group_match,
    _create_match,
    _delete_group_matches,
    _delete_group_teams_and_groups,
    _ensure_groups_fully_assigned,
    _generate_round_robin,
    _get_league_or_404,
    _get_tournament_or_404,
    _get_tournament_teams,
    _load_groups_with_teams,
    _load_team_league_map,
    _order_matches,
    _resolve_match_league_id,
)


@router.post("/{tournament_id}/groups/auto", response_model=TournamentStructureResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
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
        _delete_group_matches(db, group_ids)
        _delete_group_teams_and_groups(db, tournament_id, group_ids)

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


@router.post("/{tournament_id}/groups/schedule", response_model=TournamentStructureResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
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
    _ensure_groups_fully_assigned(tournament, groups)

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
        _delete_group_matches(db, group_ids, existing_matches)

    team_ids_all = _collect_group_team_ids(groups)
    team_leagues = _load_team_league_map(db, tournament_id, team_ids_all)

    _get_league_or_404(db, tournament_id, data.leagueId)

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

    for index, spec in enumerate(ordered_specs, start=1):
        match = _create_match(
            db,
            team1_id=spec["team1Id"],
            team2_id=spec["team2Id"],
            timestamp=data.startTimestamp + interval * (index - 1),
            league_id=spec["leagueId"],
        )
        _create_group_match(
            db,
            group_id=spec["groupId"],
            match_id=match.id,
            round_number=spec["round"],
            order=index,
        )

    db.commit()

    return await get_tournament_structure(tournament_id, db)


@router.post("/{tournament_id}/groups/schedule/reset", response_model=TournamentStructureResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
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
    _delete_group_matches(db, group_ids)

    db.commit()
    return await get_tournament_structure(tournament_id, db)


@router.delete("/{tournament_id}/group-schedule", response_model=TournamentStructureResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def delete_group_schedule(
    tournament_id: int,
    db: Session = Depends(get_db),
):
    return await reset_group_schedule(tournament_id, db)


@router.post("/{tournament_id}/group-schedule", response_model=TournamentStructureResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
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


@router.get("/{tournament_id}/groups/matches", response_model=TournamentGroupMatchesResponse, dependencies=[Depends(JwtRequired())])
async def get_group_matches(
    tournament_id: int,
    db: Session = Depends(get_db),
):
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


@router.get("/{tournament_id}/groups/standings", response_model=TournamentGroupStandingsResponse, dependencies=[Depends(JwtRequired())])
async def get_group_standings(
    tournament_id: int,
    db: Session = Depends(get_db),
):
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
