from datetime import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, BigInteger
from sqlalchemy.orm import relationship

from constants.match_state import MatchState
from extensions import BaseModel
from modules.attendance.models.attendance_model import AttendanceModel  # noqa: F401


class MatchModel(BaseModel):
    __tablename__ = "matches"

    id = Column(BigInteger, primary_key=True, index=True)
    team1Id = Column(BigInteger, ForeignKey("teams.id"), nullable=False, name="team1_id")
    team2Id = Column(BigInteger, ForeignKey("teams.id"), nullable=False, name="team2_id")
    _location = Column(String, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    scoreTeam1 = Column(Integer, nullable=True, name="score_team1")
    scoreTeam2 = Column(Integer, nullable=True, name="score_team2")
    state = Column(Enum(MatchState), default=MatchState.SCHEDULED)
    leagueId = Column(BigInteger, ForeignKey("leagues.id"), nullable=True, name="league_id")

    team1 = relationship("TeamModel", foreign_keys=[team1Id])
    team2 = relationship("TeamModel", foreign_keys=[team2Id])
    league = relationship("LeagueModel")
    goals = relationship("GoalModel", back_populates="match")
    attendance = relationship("AttendanceModel", back_populates="match")

    @property
    def location(self):
        return self._location if self._location else self.team1.location

    @location.setter
    def location(self, value):
        self._location = value
