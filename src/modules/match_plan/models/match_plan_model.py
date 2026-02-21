from datetime import datetime

from sqlalchemy import Column, DateTime, String, BigInteger

from extensions import BaseModel


class MatchPlanModel(BaseModel):
    __tablename__ = "match_plans"

    id = Column(BigInteger, primary_key=True, index=True)
    matchDate = Column(DateTime, nullable=True, name="match_date")
    location = Column(String, nullable=True)
    formation = Column(String, nullable=False, default="2-2-1")
    opponentName = Column(String, nullable=True, name="opponent_name")
    opponentNotes = Column(String, nullable=True, name="opponent_notes")
    playerIds = Column(String, nullable=True, name="player_ids")
    createdAt = Column(DateTime, default=datetime.utcnow, name="created_at")
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, name="updated_at")
