from datetime import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, BigInteger, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from constants.match_state import MatchState
from extensions import BaseModel
from modules.team.models.team_model import TeamModel


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

    team1 = relationship("TeamModel", foreign_keys=[team1Id])
    team2 = relationship("TeamModel", foreign_keys=[team2Id])
    goals = relationship("GoalModel", back_populates="match")

    @hybrid_property
    def location(self):
        return self._location if self._location else self.team1.location

    @location.setter
    def location(self, value):
        self._location = value

    @hybrid_property
    def leagueId(self):
        return self.team1.leagueId

    @leagueId.expression
    def leagueId(cls):
        return (
            select(TeamModel.leagueId)
            .where(TeamModel.id == cls.team1Id)
            .correlate(cls)
            .scalar_subquery()
        )
