from pydantic import BaseModel, Field


class ConfirmationResponse(BaseModel):
    message: str = Field("Process was succesful", example="Process was succesful")
