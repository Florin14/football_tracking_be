from fastapi import Depends
from sqlalchemy.orm import Session

from extensions import get_db
from modules.player.models.player_model import PlayerModel
from modules.player.models.player_schemas import PlayerResponse, PlayerUpdate
from .router import router


@router.put("/{id}", response_model=PlayerResponse)
async def update_player(playerId: int, playerData: PlayerUpdate, db: Session = Depends(get_db)):
    """Update a player"""
    player = db.query(PlayerModel).filter(PlayerModel.id == playerId).first()

    if playerData.name:
        player.name = playerData.name

    if playerData.email:
        # Check if new email already exists (excluding current player)
        existing_player = db.query(PlayerModel).filter(
            PlayerModel.email == playerData.email,
            PlayerModel.id != playerId
        ).first()

        player.email = playerData.email

    if playerData.position:
        player.position = playerData.position

    if playerData.rating is not None:
        player.rating = playerData.rating

    db.commit()
    db.refresh(player)

    return PlayerResponse(
        id=player.id,
        name=player.name,
        email=player.email,
        position=player.position if player.position else None,
        rating=player.rating,
        teamId=player.teamId,
        teamName=player.team.name if player.team else None
    )
