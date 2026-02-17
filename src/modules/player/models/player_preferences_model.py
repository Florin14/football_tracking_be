from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import relationship

from constants.player_positions import PlayerPositions
from constants.preferred_language import PreferredLanguage
from extensions import BaseModel


class PlayerPreferencesModel(BaseModel):
    __tablename__ = "player_preferences"

    id = Column(BigInteger, primary_key=True, index=True)
    playerId = Column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False, unique=True, name="player_id")
    preferredPosition = Column(Enum(PlayerPositions), nullable=True, name="preferred_position")
    preferredLanguage = Column(Enum(PreferredLanguage), nullable=True, name="preferred_language")
    nickname = Column(String(50), nullable=True)
    receiveEmailNotifications = Column(Boolean, nullable=False, default=True, name="receive_email_notifications")
    receiveMatchReminders = Column(Boolean, nullable=False, default=True, name="receive_match_reminders")
    createdAt = Column(DateTime, nullable=False, default=datetime.utcnow, name="created_at")
    updatedAt = Column(DateTime, nullable=True, onupdate=datetime.utcnow, name="updated_at")

    player = relationship("PlayerModel", back_populates="preferences")
