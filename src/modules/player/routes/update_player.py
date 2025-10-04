from fastapi import Depends
from sqlalchemy.orm import Session

from extensions import get_db
from modules.player.models.player_model import PlayerModel
from modules.player.models.player_schemas import PlayerResponse, PlayerUpdate
from project_helpers.dependencies import GetInstanceFromPath
from .router import router


@router.put("/{id}", response_model=PlayerResponse)
async def update_player(data: PlayerUpdate, player: PlayerModel = Depends(GetInstanceFromPath(PlayerModel)),
                        db: Session = Depends(get_db)):
    if data.name:
        player.name = data.name

        # if data.email:
        #     # Check if new email already exists (excluding current player)
        #     existing_player = db.query(PlayerModel).filter(
        #         PlayerModel.email == data.email,
        #         PlayerModel.id != playerId
        #     ).first()

        player.email = data.email

    if data.position:
        player.position = data.position

    if data.avatar:
        player.avatar = data.avatar

    if data.rating is not None:
        player.rating = data.rating

    db.commit()
    db.refresh(player)

    return PlayerResponse(
        id=player.id,
        name=player.name,
        email=player.email,
        position=player.position if player.position else None,
        rating=player.rating,
        avatar=player.avatar,
        # teamId=player.teamId,
        # teamName=player.team.name if player.team else None
    )
