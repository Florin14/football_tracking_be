from fastapi import Depends
from sqlalchemy.orm import Session, joinedload

from constants.platform_roles import PlatformRoles
from extensions import get_db
from modules.player.models.player_model import PlayerModel
from modules.player.models.player_schemas import PlayerProfileResponse
from project_helpers.dependencies import GetCurrentUser
from project_helpers.error import Error
from project_helpers.exceptions import ErrorException
from .router import router


@router.get("/profile", response_model=PlayerProfileResponse)
async def get_player_profile(
    db: Session = Depends(get_db),
    current_user: PlayerModel = Depends(GetCurrentUser(roles=[PlatformRoles.PLAYER])),
):
    player = (
        db.query(PlayerModel)
        .options(
            joinedload(PlayerModel.team),
            joinedload(PlayerModel.preferences),
        )
        .filter(PlayerModel.id == current_user.id)
        .first()
    )
    if not player:
        raise ErrorException(error=Error.USER_NOT_FOUND, statusCode=404)
    return player
