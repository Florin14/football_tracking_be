from sqlalchemy import Column, DateTime, Enum, String, Boolean, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from constants.notification_type import NotificationType

from extensions import BaseModel


class NotificationModel(BaseModel):
    __tablename__ = "notifications"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    isDeleted = Column(Boolean, name="is_deleted", nullable=False, default=False)
    playerId = Column(BigInteger, ForeignKey("players.id"), name="player_id", nullable=False)
    player = relationship("PlayerModel", back_populates="notifications")
    createdAt = Column(DateTime, name="created_at", nullable=False)
    type = Column(Enum(NotificationType), nullable=False, default=NotificationType.NEW_MATCH)

    @property
    def playerCount(self):
        return 1 if self.player else 0


