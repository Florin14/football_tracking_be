from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.ranking.models.ranking_model import RankingModel
from modules.team.models import TeamModel
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.league_team_model import LeagueTeamModel
from modules.tournament.models.tournament_schemas import LeagueTeamsAssignRequest, LeagueTeamsResponse
from project_helpers.dependencies import JwtRequired

from .router import router


@router.put("/{tournament_id}/leagues/{league_id}/teams", response_model=LeagueTeamsResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def assign_league_teams(
    tournament_id: int,
    league_id: int,
    data: LeagueTeamsAssignRequest,
    db: Session = Depends(get_db),
):
    league = (
        db.query(LeagueModel)
        .filter(LeagueModel.id == league_id, LeagueModel.tournamentId == tournament_id)
        .first()
    )
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found for this tournament",
        )

    if len(set(data.teamIds)) != len(data.teamIds):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team IDs must be unique",
        )

    teams = (
        db.query(TeamModel)
        .options(joinedload(TeamModel.players))
        .filter(TeamModel.id.in_(data.teamIds))
        .all()
    )
    if len(teams) != len(data.teamIds):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more teams not found",
        )

    existing_memberships = (
        db.query(LeagueTeamModel)
        .join(LeagueModel, LeagueModel.id == LeagueTeamModel.leagueId)
        .filter(LeagueTeamModel.teamId.in_(data.teamIds))
        .all()
    )
    already_in_league = [
        membership.teamId
        for membership in existing_memberships
        if membership.leagueId == league_id
    ]
    already_in_tournament = [
        membership.teamId
        for membership in existing_memberships
        if membership.leagueId != league_id and membership.league.tournamentId == tournament_id
    ]

    if already_in_league or already_in_tournament:
        detail = {"message": "Some teams already belong to this league or tournament"}
        if already_in_league:
            detail["alreadyInLeague"] = already_in_league
        if already_in_tournament:
            detail["alreadyInTournament"] = already_in_tournament
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    for team in teams:
        db.add(LeagueTeamModel(leagueId=league_id, teamId=team.id))
        exists = db.query(RankingModel).filter_by(teamId=team.id, leagueId=league_id).first()
        if not exists:
            db.add(RankingModel(teamId=team.id, leagueId=league_id))

    db.commit()

    return LeagueTeamsResponse(
        league=league,
        teams=teams,
    )
