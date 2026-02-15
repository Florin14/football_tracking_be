import logging

from fastapi import BackgroundTasks, Depends
from sqlalchemy.orm import Session

from extensions import get_db
from constants.platform_roles import PlatformRoles
from modules.player.models.player_schemas import PlayerAdd
from modules.team.models.team_model import TeamModel
from modules.player.models.player_schemas import PlayerResponse
from project_helpers.dependencies import JwtRequired
from project_helpers.emails_handling import (
    SendEmailRequest as EmailSendRequest,
    build_message,
    send_via_gmail_oauth2_safe,
    validate_config,
    FRONTEND_URL,
)
from project_helpers.error import Error
from project_helpers.exceptions import ErrorException
from .router import router
from ..models.player_model import PlayerModel


@router.post("/base-camp", response_model=PlayerResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def add_base_camp_player(
    data: PlayerAdd,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
):
    password = "fotbal@2025"
    team = db.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()
    if team is None:
        return ErrorException(error=Error.TEAM_INSTANCE_NOT_FOUND)
    player = PlayerModel(**data.model_dump(), password=password, teamId=team.id, role=PlatformRoles.PLAYER)
    db.add(player)
    db.commit()
    db.refresh(player)

    if player.email and not player.email.endswith("@generated.local"):
        try:
            validate_config()
        except RuntimeError as exc:
            logging.warning("Welcome email not sent for player %s: %s", player.id, exc)
        else:
            template_data = {
                "player_name": player.name,
                "email": player.email,
                "password": password,
                "platform_url": FRONTEND_URL,
            }
            email_req = EmailSendRequest(
                to=[player.email],
                subject="Welcome to Football Tracking!",
            )
            msg = build_message(email_req, template_data=template_data, template_name="welcome_player.html")
            bg.add_task(send_via_gmail_oauth2_safe, msg)

    return player
