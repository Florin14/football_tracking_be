import datetime

from sqlalchemy import Boolean, Column, Date, String, ForeignKey, Integer, BigInteger, UniqueConstraint, text
from sqlalchemy.orm import relationship

from extensions import BaseModel


def season_default() -> str:
    today = datetime.date.today()
    return f"{today.year}-{today.year + 1}"


class LeagueModel(BaseModel):
    __tablename__ = "leagues"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=False)
    description = Column(String, nullable=True)
    isDefault = Column(Boolean, default=False, name="is_default")
    startDate = Column(Date, nullable=True, name="start_date")
    endDate = Column(Date, nullable=True, name="end_date")
    relevanceOrder = Column(Integer, nullable=True, name="relevance_order")
    season = Column(
        String(9),
        nullable=False,
        default=season_default,
        server_default=text("to_char(current_date, 'YYYY') || '-' || to_char(current_date + interval '1 year', 'YYYY')")
    )
    teams = relationship("TeamModel", back_populates="league")
    tournamentId = Column(BigInteger, ForeignKey("tournaments.id"), nullable=False, name="tournament_id")
    tournament = relationship("TournamentModel")

    __table_args__ = (UniqueConstraint(name, tournamentId),)
