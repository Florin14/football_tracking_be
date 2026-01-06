from sqlalchemy import Boolean, Column, LargeBinary, String, ForeignKey, BigInteger
from sqlalchemy.orm import relationship

from extensions import BaseModel


class NotificationModel(BaseModel):
    __tablename__ = "notifications"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    playerId = Column(BigInteger, ForeignKey("players.id"), name="player_id", nullable=False)
    player = relationship("PlayerModel", back_populates="notifications")


