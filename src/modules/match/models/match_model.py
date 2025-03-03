from datetime import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship

from extensions import BaseModel


class MatchState(Enum):
    SCHEDULED = "SCHEDULED"
    ONGOING = "ONGOING"
    FINISHED = "FINISHED"


class MatchModel(BaseModel):
    __tablename__ = "match"

    id = Column(Integer, primary_key=True, index=True)
    team1Id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    team2Id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    location = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    scoreTeam1 = Column(Integer, nullable=True)
    scoreTeam2 = Column(Integer, nullable=True)
    state = Column(Enum(MatchState), default=MatchState.SCHEDULED)

    team1 = relationship("Team", foreign_keys=[team1Id])
    team2 = relationship("Team", foreign_keys=[team2Id])
