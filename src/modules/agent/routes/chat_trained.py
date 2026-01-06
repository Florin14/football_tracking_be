from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from extensions import get_db
from modules.agent.agent_trained import handle_message

app = FastAPI()

class ChatIn(BaseModel):
    message: str
    state: dict | None = None

@app.post("/chat")
def chat(body: ChatIn, db: Session = Depends(get_db)):
    return handle_message(db, body.message)
