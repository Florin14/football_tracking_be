from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from extensions import BaseModel


class TournamentGroupModel(BaseModel):
    __tablename__ = "tournament_groups"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False)
    order = Column(Integer, nullable=True, name="group_order")
    tournamentId = Column(BigInteger, ForeignKey("tournaments.id"), nullable=False, name="tournament_id")

    tournament = relationship("TournamentModel", back_populates="groups")
    teams = relationship(
        "TournamentGroupTeamModel",
        back_populates="group",
        cascade="all, delete-orphan",
    )
