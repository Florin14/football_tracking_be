from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB

from extensions import BaseModel


class AgentCrudSessionModel(BaseModel):
    __tablename__ = "agent_crud_sessions"

    id = Column(BigInteger, primary_key=True, index=True)
    conversationId = Column(BigInteger, ForeignKey("chat_conversations.id", ondelete="CASCADE"),
                            nullable=True, name="conversation_id")
    userId = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, name="user_id")
    intent = Column(String(50), nullable=False)
    collectedData = Column(JSONB, nullable=False, default=dict, name="collected_data")
    pendingField = Column(String(50), nullable=True, name="pending_field")
    status = Column(String(20), nullable=False, default="in_progress")
    createdAt = Column(DateTime, nullable=False, default=datetime.utcnow, name="created_at")
    updatedAt = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, name="updated_at")
