from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


# --- Chat request/response ---

class ChatIn(BaseModel):
    message: str
    conversationId: Optional[int] = None


class ChatLink(BaseModel):
    label: str
    url: str


class ChatOut(BaseModel):
    type: str
    text: str
    suggestedQuestions: Optional[List[str]] = None
    links: Optional[List[ChatLink]] = None
    conversationId: Optional[int] = None
    messageId: Optional[int] = None


# --- Conversation CRUD ---

class ConversationCreate(BaseModel):
    title: Optional[str] = None


class ConversationUpdate(BaseModel):
    title: str


class MessageOut(BaseModel):
    id: int
    sender: str
    text: str
    links: Optional[list] = None
    suggestedQuestions: Optional[list] = None
    isWelcome: bool = False
    createdAt: datetime

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    id: int
    title: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime
    messages: List[MessageOut] = []

    class Config:
        from_attributes = True


class ConversationListItem(BaseModel):
    id: int
    title: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    conversations: List[ConversationListItem]
    total: int
