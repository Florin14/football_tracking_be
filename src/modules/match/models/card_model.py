from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, BigInteger
from sqlalchemy.orm import relationship

from constants.card_type import CardType
from extensions import BaseModel


class CardModel(BaseModel):
    __tablename__ = "cards"

    id = Column(BigInteger, primary_key=True, index=True)
    matchId = Column(BigInteger, ForeignKey("matches.id"), nullable=False)
    playerId = Column(BigInteger, ForeignKey("players.id"), nullable=False)
    teamId = Column(BigInteger, ForeignKey("teams.id"), nullable=False)
    cardType = Column(Enum(CardType), nullable=False, name="card_type")
    minute = Column(Integer, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    match = relationship("MatchModel")
    player = relationship("PlayerModel")
    team = relationship("TeamModel")
