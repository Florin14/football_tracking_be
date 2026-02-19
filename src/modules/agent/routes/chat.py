from __future__ import annotations

from typing import List, Optional

from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.agent.agent import handle_message
from .router import router


class ChatIn(BaseModel):
    message: str


class ChatLink(BaseModel):
    label: str
    url: str


class ChatOut(BaseModel):
    type: str
    text: str
    suggestedQuestions: Optional[List[str]] = None
    links: Optional[List[ChatLink]] = None


@router.post("/chat", response_model=ChatOut)
def chat(body: ChatIn, db: Session = Depends(get_db)):
    result = handle_message(db, body.message)
    return result
