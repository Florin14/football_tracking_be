from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from extensions import BaseModel


class ChatConversationModel(BaseModel):
    __tablename__ = "chat_conversations"

    id = Column(BigInteger, primary_key=True, index=True)
    userId = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, name="user_id")
    title = Column(String(255), nullable=True)
    createdAt = Column(DateTime, nullable=False, default=datetime.utcnow, name="created_at")
    updatedAt = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, name="updated_at")

    messages = relationship("ChatMessageModel", back_populates="conversation", cascade="all, delete-orphan",
                            order_by="ChatMessageModel.createdAt")
