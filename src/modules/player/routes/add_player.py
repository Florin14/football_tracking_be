from fastapi import Depends
from sqlalchemy.orm import Session

from extensions import get_db
from modules.user.models.user_model import UserModel
from modules.user.models.user_schemas import UserAdd, UserResponse
from .router import router
from ..models.player_model import PlayerModel
from modules.player.models.player_schemas import PlayerAdd


@router.post("", response_model=UserResponse)
async def add_player(data: PlayerAdd, db: Session = Depends(get_db)):
    password = "fotbal@2025"
    player = PlayerModel(**data.model_dump(), password=password)
    db.add(player)
    db.commit()
    db.refresh(player)
    return player
