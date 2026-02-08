
from fastapi import Depends
from sqlalchemy.orm import Session, joinedload

from extensions import get_db
from project_helpers.dependencies import JwtRequired
from modules.player.models.player_model import PlayerModel
from modules.player.models.player_schemas import PlayerListParams, PlayerListResponse
from .router import router


@router.get("/free-agents/", response_model=PlayerListResponse)
async def get_free_agents(
        params: PlayerListParams = Depends(),
        db: Session = Depends(get_db),
        current_user=Depends(JwtRequired()),
):
    """Get players without a team (free agents)"""
    query = db.query(PlayerModel).options(joinedload(PlayerModel.team)).filter(PlayerModel.teamId == None)

    if params.position:
        query = query.filter(PlayerModel.position == params.position)

    players = params.apply(query).all()

    return PlayerListResponse(data=players)
