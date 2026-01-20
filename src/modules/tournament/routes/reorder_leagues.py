from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.tournament_schemas import LeagueReorderRequest, LeaguesListResponse

from .router import router


@router.put("/{tournament_id}/leagues/reorder", response_model=LeaguesListResponse)
async def reorder_leagues(
    tournament_id: int,
    data: LeagueReorderRequest,
    db: Session = Depends(get_db),
):
    if len(set(data.leagueIds)) != len(data.leagueIds):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="League IDs must be unique",
        )

    leagues = (
        db.query(LeagueModel)
        .filter(
            LeagueModel.id.in_(data.leagueIds),
            LeagueModel.tournamentId == tournament_id,
        )
        .all()
    )

    if len(leagues) != len(data.leagueIds):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more leagues not found for this tournament",
        )

    league_by_id = {league.id: league for league in leagues}
    for index, league_id in enumerate(data.leagueIds, start=1):
        league_by_id[league_id].relevanceOrder = index

    db.commit()

    ordered_leagues = (
        db.query(LeagueModel)
        .filter(LeagueModel.tournamentId == tournament_id)
        .order_by(LeagueModel.relevanceOrder.is_(None), LeagueModel.relevanceOrder)
        .all()
    )

    leagues_items = []
    for league in ordered_leagues:
        leagues_items.append({
            "id": league.id,
            "name": league.name,
            "relevanceOrder": league.relevanceOrder,
        })

    return LeaguesListResponse(data=leagues_items)
