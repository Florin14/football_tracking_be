from typing import List, Optional

from pydantic import Field, validator

from modules.player.models.player_schemas import PlayerResponse
from project_helpers.functions import process_and_convert_image_to_base64
from project_helpers.schemas import BaseSchema, FilterSchema


class TeamAdd(BaseSchema):
    name: str = Field(..., max_length=50, example="Nordic Lions")
    description: Optional[str] = Field(None, max_length=200, example="Professional football team")
    logo: Optional[bytes] = Field(None)

    @validator("logo", pre=False, always=True)
    def encode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return process_and_convert_image_to_base64(value, 316)
        return value


class TeamUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    logo: Optional[bytes] = Field(None)

    @validator("logo", pre=False, always=True)
    def encode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return process_and_convert_image_to_base64(value, 316)
        return value


class AddPlayerToTeam(BaseSchema):
    playerId: int = Field(..., example=1)


class TeamItem(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    playerCount: Optional[int] = 0
    logo: Optional[str] = Field(None, example="")

    @validator("logo", pre=False, always=True)
    def decode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value


class TeamFilter(FilterSchema):
    sortBy: str = "name"


class TeamResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    players: Optional[List[dict]] = []
    logo: Optional[bytes] = Field(None, example="")

    @validator("logo", pre=False, always=True)
    def decode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value


class NordicTeamResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    players: Optional[List[PlayerResponse]] = []
    logo: Optional[bytes] = Field(None, example="")

    @validator("logo", pre=False, always=True)
    def decode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value


class TeamListResponse(BaseSchema):
    data: List[TeamItem] = []
