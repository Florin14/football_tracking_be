from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from extensions import BaseModel


class ChatMessageModel(BaseModel):
    __tablename__ = "chat_messages"

    id = Column(BigInteger, primary_key=True, index=True)
    conversationId = Column(BigInteger, ForeignKey("chat_conversations.id", ondelete="CASCADE"),
                            nullable=False, name="conversation_id")
    sender = Column(String(10), nullable=False)  # USER / AGENT / SYSTEM
    text = Column(Text, nullable=False)
    links = Column(JSONB, nullable=True)
    suggestedQuestions = Column(JSONB, nullable=True, name="suggested_questions")
    isWelcome = Column(Boolean, nullable=False, default=False, name="is_welcome")
    createdAt = Column(DateTime, nullable=False, default=datetime.utcnow, name="created_at")

    conversation = relationship("ChatConversationModel", back_populates="messages")
