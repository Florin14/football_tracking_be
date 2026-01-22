import datetime

from sqlalchemy import Boolean, Column, Date, String, ForeignKey, Integer, BigInteger, UniqueConstraint, text, event, func, select
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
    leagueTeams = relationship(
        "LeagueTeamModel",
        back_populates="league",
        cascade="all, delete-orphan",
    )
    teams = relationship("TeamModel", secondary="league_teams", viewonly=True)
    tournamentId = Column(BigInteger, ForeignKey("tournaments.id"), nullable=False, name="tournament_id")
    tournament = relationship("TournamentModel")

    __table_args__ = (UniqueConstraint(name, tournamentId),)


@event.listens_for(LeagueModel, "before_insert")
def set_default_relevance_order(mapper, connection, target):
    _ensure_relevance_order(connection, target)


@event.listens_for(LeagueModel, "before_update")
def ensure_relevance_order_on_update(mapper, connection, target):
    _ensure_relevance_order(connection, target)


def _ensure_relevance_order(connection, target):
    if target.relevanceOrder is not None:
        return

    max_order_query = select(func.max(LeagueModel.relevanceOrder))
    max_order = connection.execute(max_order_query).scalar()
    target.relevanceOrder = (max_order or 0) + 1
