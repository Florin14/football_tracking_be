from sqlalchemy import BigInteger, Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from extensions import BaseModel


class TournamentGroupMatchModel(BaseModel):
    __tablename__ = "tournament_group_matches"

    id = Column(BigInteger, primary_key=True, index=True)
    groupId = Column(BigInteger, ForeignKey("tournament_groups.id"), nullable=False, name="group_id")
    matchId = Column(BigInteger, ForeignKey("matches.id"), nullable=False, name="match_id")
    round = Column(Integer, nullable=True, name="round")
    order = Column(Integer, nullable=True, name="match_order")

    group = relationship("TournamentGroupModel")
    match = relationship("MatchModel")
