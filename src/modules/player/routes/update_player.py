from fastapi import BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions import get_db
from modules.player.models.player_model import PlayerModel
from modules.player.models.player_schemas import PlayerResponse, PlayerUpdate
from project_helpers.dependencies import GetInstanceFromPath, JwtRequired
from project_helpers.emails_handling import send_welcome_email, get_admin_lang
from .router import router


@router.put("/{id:int}", response_model=PlayerResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def update_player(
    data: PlayerUpdate,
    request: Request,
    bg: BackgroundTasks,
    player: PlayerModel = Depends(GetInstanceFromPath(PlayerModel)),
    db: Session = Depends(get_db),
):
    previous_email = player.email
    should_send_welcome_email = False

    if data.name:
        player.name = data.name

    if data.email:
        existing_player = db.query(PlayerModel).filter(
            PlayerModel.email == data.email,
            PlayerModel.id != player.id
        ).first()
        if existing_player:
            raise HTTPException(status_code=409, detail="EMAIL_ALREADY_IN_USE")
        player.email = data.email

        should_send_welcome_email = (
            data.email != previous_email
            and not data.email.endswith("@generated.local")
        )

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

    if should_send_welcome_email:
        admin_lang = get_admin_lang(db, request.state.user)
        send_welcome_email(bg, db, player, lang=admin_lang)

    return player

