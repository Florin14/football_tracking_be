from typing import Optional

from pydantic import BaseModel, Field


class ConfirmationResponse(BaseModel):
    message: Optional[str] = Field("Process was succesful", example="Process was succesful")
