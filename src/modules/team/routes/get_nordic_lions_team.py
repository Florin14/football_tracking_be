from fastapi import Depends
from fastapi import Depends
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.team.models import TeamModel, TeamResponse
from .router import router


@router.get("/nordic-lions", response_model=TeamResponse)
async def get_nordic_lions_team(db: Session = Depends(get_db)):
    team = db.query(TeamModel).options(joinedload(TeamModel.players)).filter(
        TeamModel.isDefault.is_(True)
    ).first()

    if not team:
        # Create the team if it doesn't exist
        team = TeamModel(
            name="Nordic Lions",
            description="The default team for the Nordic Lions football club",
            isDefault=True  # Assuming you want to mark it as default
        )
        db.add(team)
        db.commit()
        db.refresh(team)

    players = []
    if team.players:
        for player in team.players:
            players.append({
                "id": player.id,
                "name": player.name,
                "email": player.email,
                "avatar": player.avatar,
                "shirtNumber": player.shirtNumber,
                "position": player.position.value if player.position else None,
                "rating": player.rating
            })

    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        players=players,
        logo=team.logo,
    )
