from sqlalchemy import Column, DateTime, Enum, String, Boolean, ForeignKey, BigInteger
from constants.notification_type import NotificationType

from extensions import BaseModel


class NotificationModel(BaseModel):
    __tablename__ = "notifications"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    isDeleted = Column(Boolean, name="is_deleted", nullable=False, default=False)
    userId = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), name="user_id", nullable=False)
    createdAt = Column(DateTime, name="created_at", nullable=False)
    type = Column(Enum(NotificationType), nullable=False, default=NotificationType.NEW_MATCH)


