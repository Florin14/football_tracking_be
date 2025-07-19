from datetime import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, BigInteger
from sqlalchemy.orm import relationship

from constants.match_state import MatchState
from extensions import BaseModel


class MatchModel(BaseModel):
    __tablename__ = "matches"

    id = Column(BigInteger, primary_key=True, index=True)
    team1Id = Column(BigInteger, ForeignKey("teams.id"), nullable=False)
    team2Id = Column(BigInteger, ForeignKey("teams.id"), nullable=False)
    location = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    scoreTeam1 = Column(Integer, nullable=True)
    scoreTeam2 = Column(Integer, nullable=True)
    state = Column(Enum(MatchState), default=MatchState.SCHEDULED)

    team1 = relationship("TeamModel", foreign_keys=[team1Id])
    team2 = relationship("TeamModel", foreign_keys=[team2Id])
    goals = relationship("GoalModel", back_populates="match")
