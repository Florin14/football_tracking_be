"""CRUD routes for chat conversations."""
from __future__ import annotations

from datetime import datetime

from fastapi import Depends
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.agent.models.chat_conversation_model import ChatConversationModel
from modules.agent.models.chat_message_model import ChatMessageModel
from modules.agent.models.chat_schemas import (
    ConversationCreate,
    ConversationListItem,
    ConversationListResponse,
    ConversationOut,
    ConversationUpdate,
    MessageOut,
)
from modules.user.models.user_model import UserModel
from project_helpers.dependencies.jwt_required import JwtRequired
from .router import router


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(
    limit: int = 50,
    offset: int = 0,
    user: UserModel = Depends(JwtRequired()),
    db: Session = Depends(get_db),
):
    q = (
        db.query(ChatConversationModel)
        .filter(ChatConversationModel.userId == user.id)
        .order_by(ChatConversationModel.updatedAt.desc())
    )
    total = q.count()
    conversations = q.offset(offset).limit(limit).all()
    return ConversationListResponse(
        conversations=[
            ConversationListItem(
                id=c.id,
                title=c.title,
                createdAt=c.createdAt,
                updatedAt=c.updatedAt,
            )
            for c in conversations
        ],
        total=total,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: int,
    user: UserModel = Depends(JwtRequired()),
    db: Session = Depends(get_db),
):
    conv = (
        db.query(ChatConversationModel)
        .filter(
            ChatConversationModel.id == conversation_id,
            ChatConversationModel.userId == user.id,
        )
        .first()
    )
    if not conv:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationOut(
        id=conv.id,
        title=conv.title,
        createdAt=conv.createdAt,
        updatedAt=conv.updatedAt,
        messages=[
            MessageOut(
                id=m.id,
                sender=m.sender,
                text=m.text,
                links=m.links,
                suggestedQuestions=m.suggestedQuestions,
                isWelcome=m.isWelcome,
                createdAt=m.createdAt,
            )
            for m in conv.messages
        ],
    )


@router.post("/conversations", response_model=ConversationOut)
def create_conversation(
    body: ConversationCreate,
    user: UserModel = Depends(JwtRequired()),
    db: Session = Depends(get_db),
):
    conv = ChatConversationModel(
        userId=user.id,
        title=body.title,
        createdAt=datetime.utcnow(),
        updatedAt=datetime.utcnow(),
    )
    db.add(conv)
    db.flush()

    # Add welcome message
    welcome = ChatMessageModel(
        conversationId=conv.id,
        sender="AGENT",
        text="",
        isWelcome=True,
        createdAt=datetime.utcnow(),
    )
    db.add(welcome)
    db.commit()
    db.refresh(conv)

    return ConversationOut(
        id=conv.id,
        title=conv.title,
        createdAt=conv.createdAt,
        updatedAt=conv.updatedAt,
        messages=[
            MessageOut(
                id=welcome.id,
                sender=welcome.sender,
                text=welcome.text,
                isWelcome=welcome.isWelcome,
                createdAt=welcome.createdAt,
            )
        ],
    )


@router.put("/conversations/{conversation_id}", response_model=ConversationOut)
def update_conversation(
    conversation_id: int,
    body: ConversationUpdate,
    user: UserModel = Depends(JwtRequired()),
    db: Session = Depends(get_db),
):
    conv = (
        db.query(ChatConversationModel)
        .filter(
            ChatConversationModel.id == conversation_id,
            ChatConversationModel.userId == user.id,
        )
        .first()
    )
    if not conv:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.title = body.title
    conv.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(conv)
    return ConversationOut(
        id=conv.id,
        title=conv.title,
        createdAt=conv.createdAt,
        updatedAt=conv.updatedAt,
        messages=[],
    )


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    user: UserModel = Depends(JwtRequired()),
    db: Session = Depends(get_db),
):
    conv = (
        db.query(ChatConversationModel)
        .filter(
            ChatConversationModel.id == conversation_id,
            ChatConversationModel.userId == user.id,
        )
        .first()
    )
    if not conv:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()
    return {"ok": True}
