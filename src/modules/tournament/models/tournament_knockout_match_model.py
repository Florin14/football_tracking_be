from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from extensions import BaseModel


class TournamentKnockoutMatchModel(BaseModel):
    __tablename__ = "tournament_knockout_matches"

    id = Column(BigInteger, primary_key=True, index=True)
    tournamentId = Column(BigInteger, ForeignKey("tournaments.id"), nullable=False, name="tournament_id")
    matchId = Column(BigInteger, ForeignKey("matches.id"), nullable=False, name="match_id")
    round = Column(String, nullable=True, name="round")
    order = Column(Integer, nullable=True, name="match_order")

    tournament = relationship("TournamentModel", back_populates="knockoutMatches")
    match = relationship("MatchModel")

    __table_args__ = (
        UniqueConstraint("tournament_id", "round", "match_order", name="uq_knockout_tournament_round_order"),
    )
