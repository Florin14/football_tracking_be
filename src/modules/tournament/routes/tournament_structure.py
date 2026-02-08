from fastapi import Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.match.models.match_model import MatchModel
from modules.team.models import TeamModel
from modules.tournament.models.tournament_group_match_model import TournamentGroupMatchModel
from modules.tournament.models.tournament_group_model import TournamentGroupModel
from modules.tournament.models.tournament_group_team_model import TournamentGroupTeamModel
from modules.tournament.models.tournament_knockout_match_model import TournamentKnockoutMatchModel
from modules.tournament.models.tournament_model import TournamentModel
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.league_team_model import LeagueTeamModel
from modules.tournament.models.tournament_schemas import (
    TournamentGroupBulkCreateRequest,
    TournamentGroupCreateRequest,
    TournamentGroupTeamsUpdate,
    TournamentKnockoutMatchAdd,
    TournamentStructureResponse,
)
from project_helpers.dependencies import JwtRequired

from .router import router


def _validate_teams_belong_to_tournament(
    db: Session,
    tournament_id: int,
    team_ids: list[int],
) -> list[TeamModel]:
    if not team_ids:
        return []

    teams = db.query(TeamModel).filter(TeamModel.id.in_(team_ids)).all()

    if len(teams) != len(set(team_ids)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more teams not found",
        )

    memberships = (
        db.query(LeagueTeamModel.teamId)
        .join(LeagueModel, LeagueModel.id == LeagueTeamModel.leagueId)
        .filter(
            LeagueTeamModel.teamId.in_(team_ids),
            LeagueModel.tournamentId == tournament_id,
        )
        .all()
    )
    valid_team_ids = {team_id for (team_id,) in memberships}
    if valid_team_ids != set(team_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more teams do not belong to this tournament",
        )

    return teams


@router.get("/{tournament_id}/structure", response_model=TournamentStructureResponse)
async def get_tournament_structure(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(JwtRequired()),
):
    tournament = db.query(TournamentModel).filter(TournamentModel.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament with ID {tournament_id} not found",
        )

    groups = (
        db.query(TournamentGroupModel)
        .options(
            joinedload(TournamentGroupModel.teams)
            .joinedload(TournamentGroupTeamModel.team)
            .joinedload(TeamModel.players)
        )
        .filter(TournamentGroupModel.tournamentId == tournament_id)
        .order_by(
            TournamentGroupModel.order.is_(None),
            TournamentGroupModel.order,
            func.lower(TournamentGroupModel.name),
        )
        .all()
    )

    group_items = []
    for group in groups:
        team_items = []
        for group_team in group.teams:
            team = group_team.team
            team_items.append({
                "id": team.id,
                "name": team.name,
                "description": team.description,
                "logo": team.logo,
                "playerCount": len(team.players) if team.players else 0,
            })
        group_items.append({
            "id": group.id,
            "name": group.name,
            "order": group.order,
            "teams": team_items,
        })

    knockout_matches = (
        db.query(TournamentKnockoutMatchModel)
        .options(joinedload(TournamentKnockoutMatchModel.match))
        .filter(TournamentKnockoutMatchModel.tournamentId == tournament_id)
        .order_by(
            TournamentKnockoutMatchModel.order.is_(None),
            TournamentKnockoutMatchModel.order,
            TournamentKnockoutMatchModel.id,
        )
        .all()
    )

    knockout_items = []
    for knockout in knockout_matches:
        match = knockout.match
        if not match:
            continue
        knockout_items.append({
            "id": knockout.id,
            "matchId": match.id,
            "round": knockout.round,
            "order": knockout.order,
            "team1Id": match.team1Id,
            "team2Id": match.team2Id,
            "scoreTeam1": match.scoreTeam1,
            "scoreTeam2": match.scoreTeam2,
            "state": match.state.value if hasattr(match.state, "value") else str(match.state),
            "timestamp": match.timestamp,
        })

    return TournamentStructureResponse(
        tournamentId=tournament.id,
        formatType=tournament.formatType,
        groupCount=tournament.groupCount,
        teamsPerGroup=tournament.teamsPerGroup,
        hasKnockout=tournament.hasKnockout,
        groups=group_items,
        knockoutMatches=knockout_items,
    )


@router.post("/{tournament_id}/groups", response_model=TournamentStructureResponse)
async def add_tournament_group(
    tournament_id: int,
    data: TournamentGroupCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(JwtRequired(roles=[PlatformRoles.ADMIN])),
):
    if data.groups:
        return await add_tournament_groups_bulk(
            tournament_id,
            TournamentGroupBulkCreateRequest(groups=data.groups, replaceExisting=data.replaceExisting),
            db,
        )

    tournament = db.query(TournamentModel).filter(TournamentModel.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament with ID {tournament_id} not found",
        )

    if not data.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name is required",
        )

    order_value = data.order
    if order_value is None:
        max_order = (
            db.query(func.max(TournamentGroupModel.order))
            .filter(TournamentGroupModel.tournamentId == tournament_id)
            .scalar()
        )
        order_value = (max_order or 0) + 1

    _validate_teams_belong_to_tournament(db, tournament_id, data.teamIds)

    group = TournamentGroupModel(
        name=data.name,
        order=order_value,
        tournamentId=tournament_id,
    )
    db.add(group)
    db.flush()

    if data.teamIds:
        for team_id in data.teamIds:
            db.add(TournamentGroupTeamModel(groupId=group.id, teamId=team_id))

    db.commit()

    return await get_tournament_structure(tournament_id, db)


@router.post("/{tournament_id}/groups/bulk", response_model=TournamentStructureResponse)
async def add_tournament_groups_bulk(
    tournament_id: int,
    data: TournamentGroupBulkCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(JwtRequired(roles=[PlatformRoles.ADMIN])),
):
    tournament = db.query(TournamentModel).filter(TournamentModel.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament with ID {tournament_id} not found",
        )

    existing_groups = (
        db.query(TournamentGroupModel.id)
        .filter(TournamentGroupModel.tournamentId == tournament_id)
        .all()
    )
    if existing_groups and not data.replaceExisting:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Groups already exist for this tournament",
        )

    group_count = tournament.groupCount
    teams_per_group = tournament.teamsPerGroup
    groups_payload = data.groups or []
    if group_count is not None and len(groups_payload) != group_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group count does not match tournament configuration",
        )

    all_team_ids: list[int] = []
    for group in groups_payload:
        if teams_per_group is not None and len(group.teamIds) != teams_per_group:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Group size does not match tournament configuration",
            )
        all_team_ids.extend(group.teamIds)

    if len(all_team_ids) != len(set(all_team_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team IDs must be unique across groups",
        )

    if group_count is not None and teams_per_group is not None:
        expected_total = group_count * teams_per_group
        if len(all_team_ids) != expected_total:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Team count does not match tournament configuration",
            )

    _validate_teams_belong_to_tournament(db, tournament_id, all_team_ids)

    if data.replaceExisting:
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
            db.query(TournamentGroupTeamModel).filter(
                TournamentGroupTeamModel.groupId.in_(group_ids)
            ).delete(synchronize_session=False)
        db.query(TournamentGroupModel).filter(
            TournamentGroupModel.tournamentId == tournament_id
        ).delete(synchronize_session=False)

    created_groups = []
    for index, group in enumerate(groups_payload, start=1):
        order_value = group.order if group.order is not None else index
        created = TournamentGroupModel(
            name=group.name,
            order=order_value,
            tournamentId=tournament_id,
        )
        db.add(created)
        created_groups.append((created, group.teamIds))
    db.flush()

    for group, team_ids in created_groups:
        for team_id in team_ids:
            db.add(TournamentGroupTeamModel(groupId=group.id, teamId=team_id))

    db.commit()
    return await get_tournament_structure(tournament_id, db)


@router.put("/groups/{group_id}/teams", response_model=TournamentStructureResponse)
async def update_group_teams(
    group_id: int,
    data: TournamentGroupTeamsUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(JwtRequired(roles=[PlatformRoles.ADMIN])),
):
    group = db.query(TournamentGroupModel).filter(TournamentGroupModel.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_id} not found",
        )

    _validate_teams_belong_to_tournament(db, group.tournamentId, data.teamIds)

    db.query(TournamentGroupTeamModel).filter(TournamentGroupTeamModel.groupId == group_id).delete()
    for team_id in data.teamIds:
        db.add(TournamentGroupTeamModel(groupId=group_id, teamId=team_id))

    db.commit()

    return await get_tournament_structure(group.tournamentId, db)


@router.post("/{tournament_id}/knockout-matches", response_model=TournamentStructureResponse)
async def add_knockout_match(
    tournament_id: int,
    data: TournamentKnockoutMatchAdd,
    db: Session = Depends(get_db),
    current_user=Depends(JwtRequired(roles=[PlatformRoles.ADMIN])),
):
    tournament = db.query(TournamentModel).filter(TournamentModel.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament with ID {tournament_id} not found",
        )

    match = (
        db.query(MatchModel)
        .filter(MatchModel.id == data.matchId)
        .first()
    )
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match with ID {data.matchId} not found",
        )

    memberships = (
        db.query(LeagueTeamModel.teamId)
        .join(LeagueModel, LeagueModel.id == LeagueTeamModel.leagueId)
        .filter(
            LeagueTeamModel.teamId.in_([match.team1Id, match.team2Id]),
            LeagueModel.tournamentId == tournament_id,
        )
        .all()
    )
    if len({team_id for (team_id,) in memberships}) != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Match teams do not belong to this tournament",
        )

    db.add(TournamentKnockoutMatchModel(
        tournamentId=tournament_id,
        matchId=data.matchId,
        round=data.round,
        order=data.order,
    ))
    db.commit()

    return await get_tournament_structure(tournament_id, db)
