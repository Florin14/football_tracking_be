from pydantic import ConfigDict, Field, BaseModel
from datetime import datetime


class FileSchema(BaseModel):
    id: str
    name: str
    folder: str
    createdAt: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
