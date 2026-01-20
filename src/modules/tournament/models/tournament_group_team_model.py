from sqlalchemy import BigInteger, Column, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from extensions import BaseModel


class TournamentGroupTeamModel(BaseModel):
    __tablename__ = "tournament_group_teams"

    id = Column(BigInteger, primary_key=True, index=True)
    groupId = Column(BigInteger, ForeignKey("tournament_groups.id"), nullable=False, name="group_id")
    teamId = Column(BigInteger, ForeignKey("teams.id"), nullable=False, name="team_id")

    group = relationship("TournamentGroupModel", back_populates="teams")
    team = relationship("TeamModel")

    __table_args__ = (UniqueConstraint(groupId, teamId),)
