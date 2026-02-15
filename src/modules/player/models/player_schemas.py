from typing import List, Optional

from pydantic import AliasChoices, Field, validator

from project_helpers.functions import process_and_convert_image_to_base64
from project_helpers.schemas import BaseSchema, FilterSchema, PaginationParams


class PlayerAdd(BaseSchema):
    name: str = Field(..., max_length=50, example="John Doe")
    email: Optional[str] = Field(..., max_length=100, example="john.doe@example.com")
    position: str = Field(..., example="FORWARD")  # Should match PlayerPositions enum
    rating: Optional[int] = Field(None, ge=0, le=100, example=85)
    shirtNumber: Optional[int] = Field(None, ge=0, le=999, example=10)

    avatar: Optional[bytes] = Field(None)

    @validator("avatar", pre=False, always=True)
    def encode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, (bytes, bytearray)) and len(value) == 0:
            return None
        if isinstance(value, str) and value == "":
            return None
        if isinstance(value, bytes):
            return process_and_convert_image_to_base64(value, 316)
        return value


class PlayerUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=40)
    position: Optional[str] = None
    rating: Optional[int] = Field(None, ge=0, le=100)
    shirtNumber: Optional[int] = Field(None, ge=0, le=999)
    avatar: Optional[bytes] = Field(None)

    @validator("avatar", pre=False, always=True)
    def encode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, (bytes, bytearray)) and len(value) == 0:
            return None
        if isinstance(value, str) and value == "":
            return None
        if isinstance(value, bytes):
            return process_and_convert_image_to_base64(value, 316)
        return value


class PlayerPreferencesUpdate(BaseSchema):
    preferredPosition: Optional[str] = None
    preferredLanguage: Optional[str] = None
    nickname: Optional[str] = Field(None, max_length=50)
    receiveEmailNotifications: Optional[bool] = None
    receiveMatchReminders: Optional[bool] = None


class PlayerPreferencesResponse(BaseSchema):
    preferredPosition: Optional[str] = None
    preferredLanguage: Optional[str] = None
    nickname: Optional[str] = None
    receiveEmailNotifications: Optional[bool] = True
    receiveMatchReminders: Optional[bool] = True


class PlayerProfileUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=40)
    position: Optional[str] = None
    shirtNumber: Optional[int] = Field(None, ge=0, le=999)
    avatar: Optional[bytes] = Field(None)
    preferences: Optional[PlayerPreferencesUpdate] = None

    @validator("avatar", pre=False, always=True)
    def encode_profile_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, (bytes, bytearray)) and len(value) == 0:
            return None
        if isinstance(value, str) and value == "":
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
    avatar: Optional[str] = Field(None, example="")

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


class PlayerListParams(PaginationParams):
    teamId: Optional[int] = Field(None, validation_alias=AliasChoices("teamId", "team_id"))
    position: Optional[str] = None
    search: Optional[str] = None


class PlayerResponse(BaseSchema):
    id: int
    name: str
    email: str
    position: Optional[str] = None
    rating: Optional[int] = None
    shirtNumber: Optional[int] = None
    teamId: Optional[int] = None
    teamName: Optional[str] = None
    goals: Optional[int] = 0
    assists: Optional[int] = 0
    appearances: Optional[int] = 0
    yellowCards: Optional[int] = 0
    redCards: Optional[int] = 0
    avatar: Optional[str] = Field(None, example="")

    @validator("avatar", pre=False, always=True)
    def decode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value


class PlayerProfileResponse(PlayerResponse):
    preferences: Optional[PlayerPreferencesResponse] = None


class PlayerListResponse(BaseSchema):
    data: List[PlayerItem] = []
