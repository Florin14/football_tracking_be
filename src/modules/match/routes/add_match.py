from datetime import datetime, timedelta
from app.services.background_jobs import send_notification

@router.post("/matches")
async def schedule_match(match: MatchCreate, db: Session = Depends(get_db)):
    db_match = MatchModel(date=match.date, location=match.location)
    db.add(db_match)
    db.commit()

    # Programare notificare
    notification_time = match.date - timedelta(hours=24)
    send_notification.apply_async(args=["player@example.com", "You have a match tomorrow!"], eta=notification_time)

    return db_match
