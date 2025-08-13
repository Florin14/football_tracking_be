from sqlalchemy import Boolean, Column, Date, String, ForeignKey, BigInteger, UniqueConstraint
from sqlalchemy.orm import relationship

from extensions import BaseModel


class LeagueModel(BaseModel):
    __tablename__ = "leagues"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=False)
    description = Column(String, nullable=True)
    isDefault = Column(Boolean, default=False, name="is_default")
    startDate = Column(Date, nullable=True, name="start_date")
    endDate = Column(Date, nullable=True, name="end_date")

    teams = relationship("TeamModel", back_populates="league")
    tournamentId = Column(BigInteger, ForeignKey("tournaments.id"), nullable=False, name="tournament_id")
    tournament = relationship("TournamentModel")

    __table_args__ = (UniqueConstraint(name, tournamentId),)

