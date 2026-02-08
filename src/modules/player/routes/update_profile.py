from fastapi import Depends
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions import get_db
from modules.player.models.player_model import PlayerModel
from modules.player.models.player_preferences_model import PlayerPreferencesModel
from modules.player.models.player_schemas import PlayerProfileResponse, PlayerProfileUpdate
from project_helpers.dependencies import JwtRequired
from project_helpers.error import Error
from project_helpers.exceptions import ErrorException
from .preferences_helpers import apply_preferences
from .router import router


@router.put("/profile", response_model=PlayerProfileResponse)
async def update_player_profile(
    data: PlayerProfileUpdate,
    current_user: PlayerModel = Depends(JwtRequired(roles=[PlatformRoles.PLAYER])),
    db: Session = Depends(get_db),
):
    player = db.query(PlayerModel).get(current_user.id)
    if not player:
        raise ErrorException(error=Error.USER_NOT_FOUND, statusCode=404)

    if data.name is not None:
        player.name = data.name

    if data.email is not None:
        player.email = data.email

    if data.position is not None:
        player.position = data.position

    if data.shirtNumber is not None:
        player.shirtNumber = data.shirtNumber

    if data.avatar is not None:
        player.avatar = data.avatar

    if data.preferences is not None:
        prefs = player.preferences
        if not prefs:
            prefs = PlayerPreferencesModel(playerId=player.id)
            db.add(prefs)
        apply_preferences(prefs, data.preferences)

    db.commit()
    db.refresh(player)

    return player
