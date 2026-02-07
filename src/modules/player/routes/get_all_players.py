from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session, joinedload

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
    query = db.query(PlayerModel).options(joinedload(PlayerModel.team))

    if teamId:
        query = query.filter(PlayerModel.teamId == teamId)

    if position:
        query = query.filter(PlayerModel.position == position)

    if search:
        query = query.filter(PlayerModel.name.ilike(f"%{search}%"))

    players = query.offset(skip).limit(limit).all()

    return PlayerListResponse(data=players)

