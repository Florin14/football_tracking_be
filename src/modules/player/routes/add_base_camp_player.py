from fastapi import Depends
from sqlalchemy.orm import Session

from extensions import get_db
from constants.platform_roles import PlatformRoles
from modules.player.models.player_schemas import PlayerAdd
from modules.team.models.team_model import TeamModel
from modules.player.models.player_schemas import PlayerResponse
from project_helpers.error import Error
from project_helpers.exceptions import ErrorException
from .router import router
from ..models.player_model import PlayerModel


@router.post("/base-camp", response_model=PlayerResponse)
async def add_base_camp_player(data: PlayerAdd, db: Session = Depends(get_db)):
    password = "fotbal@2025"
    team = db.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()
    if team is None:
        return ErrorException(error=Error.TEAM_INSTANCE_NOT_FOUND)
    player = PlayerModel(**data.model_dump(), password=password, teamId=team.id, role=PlatformRoles.PLAYER)
    db.add(player)
    db.commit()
    db.refresh(player)
    return PlayerResponse(
        id=player.id,
        name=player.name,
        email=player.email,
        position=player.position if player.position else None,
        rating=player.rating,
        avatar=player.avatar
    )
