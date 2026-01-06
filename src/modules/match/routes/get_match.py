from fastapi import Depends
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel, MatchResponse
)
from modules.team.models import TeamModel
from project_helpers.dependencies import GetInstanceFromPath
from .router import router


@router.get("/{id}", response_model=MatchResponse)
async def get_match(match: MatchModel = Depends(GetInstanceFromPath(MatchModel)), db: Session = Depends(get_db)):
    return match
