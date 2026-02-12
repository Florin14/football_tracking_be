from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions import get_db
from modules.player.models.player_model import PlayerModel
from modules.player.models.player_schemas import PlayerResponse, PlayerUpdate
from project_helpers.dependencies import GetInstanceFromPath, JwtRequired
from .router import router


@router.put("/{id}", response_model=PlayerResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def update_player(data: PlayerUpdate, player: PlayerModel = Depends(GetInstanceFromPath(PlayerModel)),
                        db: Session = Depends(get_db)):
    if data.name:
        player.name = data.name

    if data.email:
        existing_player = db.query(PlayerModel).filter(
            PlayerModel.email == data.email,
            PlayerModel.id != player.id
        ).first()
        if existing_player:
            raise HTTPException(status_code=409, detail="Email already in use")
        player.email = data.email

    if data.position:
        player.position = data.position

    if data.avatar:
        player.avatar = data.avatar

    if data.rating is not None:
        player.rating = data.rating

    if data.shirtNumber is not None:
        player.shirtNumber = data.shirtNumber

    db.commit()
    db.refresh(player)

    return player

