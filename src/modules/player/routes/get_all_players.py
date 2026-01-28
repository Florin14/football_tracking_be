from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from extensions import get_db
from modules.player.models.player_model import PlayerModel
from modules.player.models.player_schemas import PlayerFilter, PlayerListResponse
from .router import router


@router.get("", response_model=PlayerListResponse)
async def get_all_players(
        skip: int = 0,
        limit: int = 100,
        teamId: Optional[int] = None,
        position: Optional[str] = None,
        search: Optional[str] = None,
        db: Session = Depends(get_db)
):
    query = db.query(PlayerModel)

    if teamId:
        query = query.filter(PlayerModel.teamId == teamId)

    if position:
        query = query.filter(PlayerModel.position == position)

    if search:
        query = query.filter(PlayerModel.name.ilike(f"%{search}%"))

    players = query.offset(skip).limit(limit).all()

    player_items = []
    for player in players:
        player_items.append({
            "id": player.id,
            "name": player.name,
            "email": player.email,
            "position": player.position.value if player.position else None,
            "rating": player.rating,
            "teamId": player.teamId,
            "teamName": player.team.name if player.team else None,
            "goals": int(player.goalsCount or 0),
            "assists": int(player.assistsCount or 0),
            "yellowCards": int(player.yellowCardsCount or 0),
            "redCards": int(player.redCardsCount or 0),
        })

    return PlayerListResponse(data=player_items)

