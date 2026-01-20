from sqlalchemy import Boolean, Column, Date, String, ForeignKey, BigInteger, Integer
from sqlalchemy.orm import relationship

from extensions import BaseModel


class TournamentModel(BaseModel):
    __tablename__ = "tournaments"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    isDefault = Column(Boolean, default=False, name="is_default")
    formatType = Column(String, nullable=True, name="format_type")
    groupCount = Column(Integer, nullable=True, name="group_count")
    teamsPerGroup = Column(Integer, nullable=True, name="teams_per_group")
    hasKnockout = Column(Boolean, nullable=True, name="has_knockout")
    leagues = relationship("LeagueModel", back_populates="tournament")
    groups = relationship("TournamentGroupModel", back_populates="tournament", cascade="all, delete-orphan")
    knockoutMatches = relationship("TournamentKnockoutMatchModel", back_populates="tournament", cascade="all, delete-orphan")

