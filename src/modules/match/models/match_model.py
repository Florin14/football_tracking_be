from datetime import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, BigInteger
from sqlalchemy.orm import relationship

from constants.match_state import MatchState
from extensions import BaseModel


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
    round = Column(Integer, nullable=True, name="round")

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

    @property
    def team1Name(self):
        return self.team1.name if self.team1 else None

    @property
    def team2Name(self):
        return self.team2.name if self.team2 else None

    @property
    def team1Logo(self):
        return self.team1.logo if self.team1 else None

    @property
    def team2Logo(self):
        return self.team2.logo if self.team2 else None

    @property
    def leagueName(self):
        return self.league.name if self.league else None

    @property
    def leagueLogo(self):
        return self.league.logo if self.league else None
