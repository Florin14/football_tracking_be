from sqlalchemy import Column, Integer, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from datetime import datetime

from extensions import BaseModel


class GoalModel(BaseModel):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    matchId = Column(Integer, ForeignKey("matches.id"), nullable=False)
    playerId = Column(Integer, ForeignKey("players.id"), nullable=False)
    teamId = Column(Integer, ForeignKey("teams.id"), nullable=False)
    minute = Column(Integer, nullable=True)  # minute when the goal was scored
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    description = Column(String, nullable=True)  # optional description of the goal

    match = relationship("MatchModel", back_populates="goals")
    player = relationship("PlayerModel")
    team = relationship("TeamModel")
