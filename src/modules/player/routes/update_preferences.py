from fastapi import Depends, Request
from sqlalchemy.orm import Session, joinedload

from constants.platform_roles import PlatformRoles
from extensions import get_db
from modules.player.models.player_model import PlayerModel
from modules.player.models.player_preferences_model import PlayerPreferencesModel
from modules.player.models.player_schemas import PlayerPreferencesUpdate, PlayerProfileResponse
from project_helpers.dependencies import JwtRequired
from project_helpers.error import Error
from project_helpers.exceptions import ErrorException
from .preferences_helpers import apply_preferences
from .router import router


@router.put("/preferences", response_model=PlayerProfileResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.PLAYER]))])
async def update_player_preferences(
    data: PlayerPreferencesUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    auth_user = request.state.user
    player = (
        db.query(PlayerModel)
        .options(joinedload(PlayerModel.preferences))
        .filter(PlayerModel.id == auth_user.id)
        .first()
    )
    if not player:
        raise ErrorException(error=Error.USER_NOT_FOUND, statusCode=404)

    prefs = player.preferences
    if not prefs:
        prefs = PlayerPreferencesModel(playerId=player.id)
        db.add(prefs)

    apply_preferences(prefs, data)

    db.commit()
    db.refresh(player)

    return player
