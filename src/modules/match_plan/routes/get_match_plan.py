from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.match_plan.models import MatchPlanModel, MatchPlanResponse
from project_helpers.dependencies import JwtRequired
from .router import router


@router.get("/", response_model=Optional[MatchPlanResponse], dependencies=[Depends(JwtRequired())])
async def get_match_plan(
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=12)
    db.query(MatchPlanModel).filter(
        MatchPlanModel.matchDate != None,
        MatchPlanModel.matchDate < cutoff,
    ).delete(synchronize_session=False)
    db.commit()

    plan = db.query(MatchPlanModel).first()
    if not plan:
        return None

    return plan
