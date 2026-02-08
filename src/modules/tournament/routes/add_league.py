from fastapi import Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.tournament_model import TournamentModel
from modules.tournament.models.tournament_schemas import LeagueAdd, LeagueDetail
from project_helpers.dependencies import JwtRequired

from .router import router


@router.post("/{tournament_id}/leagues", response_model=LeagueDetail)
async def add_league(
    tournament_id: int,
    data: LeagueAdd,
    db: Session = Depends(get_db),
    current_user=Depends(JwtRequired(roles=[PlatformRoles.ADMIN])),
):
    tournament = db.query(TournamentModel).filter(TournamentModel.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament with ID {tournament_id} not found",
        )

    relevance_order = data.relevanceOrder
    if relevance_order is None:
        max_order = db.query(func.max(LeagueModel.relevanceOrder)).scalar()
        relevance_order = (max_order or 0) + 1

    league = LeagueModel(
        name=data.name,
        description=data.description,
        logo=data.logo,
        startDate=data.startDate,
        endDate=data.endDate,
        season=data.season,
        relevanceOrder=relevance_order,
        tournamentId=tournament_id,
    )
    db.add(league)
    db.commit()
    db.refresh(league)

    return LeagueDetail(
        id=league.id,
        name=league.name,
        description=league.description,
        logo=league.logo,
        season=league.season,
        relevanceOrder=league.relevanceOrder,
        tournamentId=league.tournamentId,
    )
