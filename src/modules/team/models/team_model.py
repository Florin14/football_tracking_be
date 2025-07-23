from sqlalchemy import Boolean, Column, LargeBinary, String, ForeignKey, BigInteger
from sqlalchemy.orm import relationship

from extensions import BaseModel


class TeamModel(BaseModel):
    __tablename__ = "teams"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    logo = Column(LargeBinary, nullable=True)
    description = Column(String, nullable=True)
    isDefault = Column(Boolean, default=False)
    players = relationship("PlayerModel", back_populates="team")
    tournamentId = Column(BigInteger, ForeignKey("tournaments.id"))
    tournament = relationship("TournamentModel")
