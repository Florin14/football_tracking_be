from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.tournament_schemas import (
    LeagueReorderItem,
    LeagueReorderRequest,
    LeaguesListResponse,
)
from project_helpers.dependencies import JwtRequired

from .router import router


def _assign_relevance_order(entries: list[LeagueReorderItem], league_by_id: dict[int, LeagueModel]):
    explicit_orders = {
        entry.leagueId: entry.relevanceOrder
        for entry in entries
        if entry.relevanceOrder is not None
    }

    order_values = list(explicit_orders.values())
    if len(order_values) != len(set(order_values)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Relevance order values must be unique within each tournament",
        )

    if any(order <= 0 for order in order_values):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Relevance order values must be greater than zero",
        )

    used_orders = set(order_values)
    next_order = 1
    for entry in entries:
        league = league_by_id[entry.leagueId]
        if entry.relevanceOrder is not None:
            league.relevanceOrder = entry.relevanceOrder
        else:
            while next_order in used_orders:
                next_order += 1
            league.relevanceOrder = next_order
            used_orders.add(next_order)
            next_order += 1


@router.put("/leagues/reorder", response_model=LeaguesListResponse, dependencies=[Depends(JwtRequired())])
async def reorder_leagues(
    data: LeagueReorderRequest,
    db: Session = Depends(get_db),
):
    league_entries: list[LeagueReorderItem] = data.leagues.copy()
    if not league_entries and data.leagueIds:
        league_entries = [LeagueReorderItem(leagueId=league_id) for league_id in data.leagueIds]

    if not league_entries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one league entry is required",
        )

    league_ids = [entry.leagueId for entry in league_entries]
    if len(set(league_ids)) != len(league_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="League IDs must be unique",
        )

    leagues = (
        db.query(LeagueModel)
        .filter(LeagueModel.id.in_(league_ids))
        .all()
    )

    if len(leagues) != len(league_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more leagues not found",
        )

    league_by_id = {league.id: league for league in leagues}
    entries_by_tournament: dict[int, list[LeagueReorderItem]] = {}
    for entry in league_entries:
        tournament_id = league_by_id[entry.leagueId].tournamentId
        entries_by_tournament.setdefault(tournament_id, []).append(entry)

    for entries in entries_by_tournament.values():
        _assign_relevance_order(entries, league_by_id)

    db.commit()

    tournament_ids = list(entries_by_tournament.keys())
    ordered_leagues = (
        db.query(LeagueModel)
        .filter(LeagueModel.tournamentId.in_(tournament_ids))
        .order_by(LeagueModel.tournamentId, LeagueModel.relevanceOrder.is_(None), LeagueModel.relevanceOrder)
        .all()
    )

    return LeaguesListResponse(data=ordered_leagues)
