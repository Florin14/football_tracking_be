from fastapi import Depends
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.team.models import TeamModel, TeamResponse
from project_helpers.dependencies import JwtRequired
from .router import router


@router.get("/base-camp", response_model=TeamResponse)
async def get_base_camp_team(
    db: Session = Depends(get_db),
):
    team = db.query(TeamModel).options(joinedload(TeamModel.players)).filter(
        TeamModel.isDefault.is_(True)
    ).first()

    if not team:
        team = TeamModel(
            name="FC Base Camp",
            description="The default team for the Base Camp football club",
            isDefault=True  # Assuming you want to mark it as default
        )
        db.add(team)
        db.commit()
        db.refresh(team)

    return team
