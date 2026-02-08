from fastapi import Depends
from sqlalchemy.orm import Session, joinedload

from extensions import get_db
from project_helpers.db import apply_search
from project_helpers.dependencies import GetCurrentUser
from modules.player.models.player_model import PlayerModel
from modules.player.models.player_schemas import PlayerListParams, PlayerListResponse
from .router import router


@router.get("", response_model=PlayerListResponse)
async def get_all_players(
        params: PlayerListParams = Depends(),
        db: Session = Depends(get_db),
        current_user=Depends(GetCurrentUser()),
):
    query = db.query(PlayerModel).options(joinedload(PlayerModel.team))

    if params.teamId:
        query = query.filter(PlayerModel.teamId == params.teamId)

    if params.position:
        query = query.filter(PlayerModel.position == params.position)

    query = apply_search(query, PlayerModel.name, params.search)

    players = params.apply(query).all()

    return PlayerListResponse(data=players)

