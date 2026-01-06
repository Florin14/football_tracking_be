from pydantic import BaseModel
from .router import router
from modules.agent.agent import handle_message


class ChatIn(BaseModel):
  message: str
  state: dict | None = None

@router.post("/chat")
def chat(body: ChatIn, user_id: str = "demo-user"):
  user_ctx = {"now_year": 2025}
  reply = handle_message(body.message, user_ctx)
  return reply
