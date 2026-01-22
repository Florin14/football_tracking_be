from sqlalchemy import BigInteger, Column, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from extensions import BaseModel


class LeagueTeamModel(BaseModel):
    __tablename__ = "league_teams"

    id = Column(BigInteger, primary_key=True, index=True)
    leagueId = Column(BigInteger, ForeignKey("leagues.id"), nullable=False, name="league_id")
    teamId = Column(BigInteger, ForeignKey("teams.id"), nullable=False, name="team_id")

    league = relationship("LeagueModel", back_populates="leagueTeams")
    team = relationship("TeamModel", back_populates="leagueTeams")

    __table_args__ = (UniqueConstraint(leagueId, teamId),)
