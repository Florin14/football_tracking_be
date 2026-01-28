from typing import List, Optional

from pydantic import Field, validator

from project_helpers.functions import process_and_convert_image_to_base64
from project_helpers.schemas import BaseSchema, FilterSchema


class PlayerAdd(BaseSchema):
    name: str = Field(..., max_length=50, example="John Doe")
    email: Optional[str] = Field(..., max_length=100, example="john.doe@example.com")
    position: str = Field(..., example="FORWARD")  # Should match PlayerPositions enum
    rating: Optional[int] = Field(None, ge=0, le=100, example=85)
    avatar: Optional[bytes] = Field(None)

    @validator("avatar", pre=False, always=True)
    def encode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return process_and_convert_image_to_base64(value, 316)
        return value


class PlayerUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=40)
    position: Optional[str] = None
    rating: Optional[int] = Field(None, ge=0, le=100)
    avatar: Optional[bytes] = Field(None)

    @validator("avatar", pre=False, always=True)
    def encode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return process_and_convert_image_to_base64(value, 316)
        return value


class PlayerItem(BaseSchema):
    id: int
    name: str
    email: Optional[str] = None
    position: Optional[str] = None
    rating: Optional[int] = None
    teamId: Optional[int] = None
    teamName: Optional[str] = None
    goals: Optional[int] = 0
    assists: Optional[int] = 0
    yellowCards: Optional[int] = 0
    redCards: Optional[int] = 0
    # teamName: Optional[str] = None
    avatar: Optional[bytes] = Field(None, example="")

    @validator("avatar", pre=False, always=True)
    def decode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value


class PlayerFilter(FilterSchema):
    teamId: Optional[int] = None
    position: Optional[str] = None
    sortBy: str = "name"


class PlayerResponse(BaseSchema):
    id: int
    name: str
    email: str
    position: Optional[str] = None
    rating: Optional[int] = None
    teamId: Optional[int] = None
    teamName: Optional[str] = None
    goals: Optional[int] = 0
    assists: Optional[int] = 0
    yellowCards: Optional[int] = 0
    redCards: Optional[int] = 0
    # teamId: Optional[int] = None
    # teamName: Optional[str] = None
    avatar: Optional[bytes] = Field(None, example="")

    @validator("avatar", pre=False, always=True)
    def decode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value


class PlayerListResponse(BaseSchema):
    data: List[PlayerItem] = []
