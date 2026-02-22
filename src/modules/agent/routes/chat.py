from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from extensions.auth_jwt import AuthJWT
from modules.agent.agent import handle_message
from modules.agent.models.chat_conversation_model import ChatConversationModel
from modules.agent.models.chat_message_model import ChatMessageModel
from modules.agent.models.chat_schemas import ChatIn, ChatOut
from modules.user.models.user_model import UserModel
from .router import router


def _get_optional_user(request: Request, db: Session = Depends(get_db), auth: AuthJWT = Depends()) -> Optional[UserModel]:
    """Try to extract the user from JWT without raising if not authenticated."""
    try:
        auth.jwt_optional()
        claims = auth.get_raw_jwt() or {}
        user_id = claims.get("userId")
        if not user_id:
            return None
        user = db.query(UserModel).get(user_id)
        return user
    except Exception:
        return None


@router.post("/chat", response_model=ChatOut)
def chat(
    body: ChatIn,
    db: Session = Depends(get_db),
    user: Optional[UserModel] = Depends(_get_optional_user),
):
    conversation_id = body.conversationId
    conversation = None

    # If authenticated, handle server-side persistence
    if user:
        if conversation_id:
            conversation = (
                db.query(ChatConversationModel)
                .filter(
                    ChatConversationModel.id == conversation_id,
                    ChatConversationModel.userId == user.id,
                )
                .first()
            )
        if not conversation:
            # Auto-create a new conversation
            conversation = ChatConversationModel(
                userId=user.id,
                createdAt=datetime.utcnow(),
                updatedAt=datetime.utcnow(),
            )
            db.add(conversation)
            db.flush()

            # Add welcome message
            welcome_msg = ChatMessageModel(
                conversationId=conversation.id,
                sender="AGENT",
                text="",
                isWelcome=True,
                createdAt=datetime.utcnow(),
            )
            db.add(welcome_msg)
            db.flush()

        # Save user message
        user_msg = ChatMessageModel(
            conversationId=conversation.id,
            sender="USER",
            text=body.message,
            createdAt=datetime.utcnow(),
        )
        db.add(user_msg)
        db.flush()

    # Process through agent
    result = handle_message(
        db,
        body.message,
        user=user,
        conversation_id=conversation.id if conversation else None,
    )

    agent_message_id = None
    if user and conversation:
        # Save agent response
        agent_msg = ChatMessageModel(
            conversationId=conversation.id,
            sender="AGENT",
            text=result.get("text", ""),
            links=result.get("links"),
            suggestedQuestions=result.get("suggestedQuestions"),
            createdAt=datetime.utcnow(),
        )
        db.add(agent_msg)

        # Update conversation title from first user message
        if not conversation.title:
            words = body.message.split()
            title_words = words[:4]
            conversation.title = " ".join(title_words) + ("..." if len(words) > 4 else "")

        conversation.updatedAt = datetime.utcnow()
        db.commit()
        db.refresh(agent_msg)
        agent_message_id = agent_msg.id

    return ChatOut(
        type=result.get("type", "answer"),
        text=result.get("text", ""),
        suggestedQuestions=result.get("suggestedQuestions"),
        links=result.get("links"),
        conversationId=conversation.id if conversation else None,
        messageId=agent_message_id,
    )
