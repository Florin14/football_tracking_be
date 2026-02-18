from fastapi import BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from extensions import get_db
from constants.platform_roles import PlatformRoles
from modules.player.models.player_schemas import PlayerAdd
from modules.team.models.team_model import TeamModel
from modules.player.models.player_schemas import PlayerResponse
from project_helpers.dependencies import JwtRequired
from project_helpers.emails_handling import send_welcome_email
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

    if data.email and not data.email.endswith("@generated.local"):
        existing = db.query(PlayerModel).filter(PlayerModel.email == data.email).first()
        if existing:
            raise HTTPException(status_code=409, detail="EMAIL_ALREADY_IN_USE")

    player = PlayerModel(**data.model_dump(), password=password, teamId=team.id, role=PlatformRoles.PLAYER)
    db.add(player)
    db.commit()
    db.refresh(player)

    send_welcome_email(bg, db, player, password)

    return player
