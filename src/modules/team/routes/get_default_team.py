from fastapi import Depends
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.team.models import TeamModel, TeamResponse
from project_helpers.dependencies import JwtRequired
from constants.platform_roles import PlatformRoles
from .router import router


@router.get("/default", response_model=TeamResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN, PlatformRoles.PLAYER]))])
async def get_default_team(
    db: Session = Depends(get_db),
):
    team = db.query(TeamModel).options(joinedload(TeamModel.players)).filter(
        TeamModel.isDefault.is_(True)
    ).first()

    if not team:
        team = TeamModel(
            name="Default Team",
            description="The default team",
            isDefault=True,
        )
        db.add(team)
        db.commit()
        db.refresh(team)

    return team


# Backward compatibility alias
@router.get("/base-camp", response_model=TeamResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN, PlatformRoles.PLAYER]))], include_in_schema=False)
async def get_base_camp_team_compat(
    db: Session = Depends(get_db),
):
    return await get_default_team(db=db)
