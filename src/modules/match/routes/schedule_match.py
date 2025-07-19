from datetime import timedelta
from extensions import get_db
from fastapi import Depends
from sqlalchemy.orm import Session
from modules.match.models.match_model import MatchModel
from modules.match.models.match_schemas import MatchAdd
from modules.match.routes.router import router

@router.post("-schedule")
async def schedule_match(match: MatchAdd, db: Session = Depends(get_db)):
    db_match = MatchModel(date=match.date, location=match.location)
    db.add(db_match)
    db.commit()

    # Programare notificare
    notification_time = match.date - timedelta(hours=24)
    # send_notification.apply_async(args=["player@example.com", "You have a match tomorrow!"], eta=notification_time)

    return db_match
