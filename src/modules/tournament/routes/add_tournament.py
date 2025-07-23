from fastapi import Depends, status
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.tournament.models import TournamentModel, TournamentAdd, TournamentResponse
from .router import router


@router.post("/", response_model=TournamentResponse)
async def add_tournament(data: TournamentAdd, db: Session = Depends(get_db)):
    tournament = TournamentModel(
        name=data.name,
        description=data.description
    )
    db.add(tournament)
    db.commit()
    db.refresh(tournament)

    return TournamentResponse(
        id=tournament.id,
        name=tournament.name,
        description=tournament.description,
    )
