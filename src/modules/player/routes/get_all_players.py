# Created by: cicada
# Date: Mon 02/03/2025
# Time: 14:11:47.00

from fastapi import Depends
from sqlalchemy.orm import Session

from extensions import get_db
from modules.player.models.player_model import PlayerModel
from modules.player.models.player_schemas import PlayerFilter, PlayerListResponse
from .router import router


@router.get('', response_model=PlayerListResponse)
async def get_all_players(query: PlayerFilter = Depends(), db: Session = Depends(get_db)):
    playerQuery = db.query(PlayerModel)

    # employerQuery = employerQuery.order_by(getattr(getattr(UserModel, query.sortBy), query.sortType)())
    # qty = employerQuery.count()
    # if None not in [query.offset, query.limit]:
    #     employerQuery = employerQuery.offset(query.offset).limit(query.limit)
    return PlayerListResponse(data=playerQuery.all())
