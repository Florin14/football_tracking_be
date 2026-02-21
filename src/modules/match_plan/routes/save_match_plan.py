import json

from fastapi import Depends
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.match_plan.models import MatchPlanModel, MatchPlanSave, MatchPlanResponse
from project_helpers.dependencies import JwtRequired
from .router import router


@router.put("/", response_model=MatchPlanResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def save_match_plan(
    data: MatchPlanSave,
    db: Session = Depends(get_db),
):
    player_ids_json = json.dumps(data.playerIds)

    plan = db.query(MatchPlanModel).first()
    if plan:
        plan.matchDate = data.matchDate
        plan.location = data.location
        plan.formation = data.formation
        plan.opponentName = data.opponentName
        plan.opponentNotes = data.opponentNotes
        plan.playerIds = player_ids_json
    else:
        plan = MatchPlanModel(
            matchDate=data.matchDate,
            location=data.location,
            formation=data.formation,
            opponentName=data.opponentName,
            opponentNotes=data.opponentNotes,
            playerIds=player_ids_json,
        )
        db.add(plan)

    db.commit()
    db.refresh(plan)

    return plan
