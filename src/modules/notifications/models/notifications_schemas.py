from typing import List, Optional

from pydantic import Field, validator

from modules.player.models.player_schemas import PlayerResponse
from project_helpers.functions import process_and_convert_image_to_base64
from project_helpers.schemas import BaseSchema, FilterSchema


class NotificationAdd(BaseSchema):
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=200)


class NotificationUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=200)


class NotificationItem(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    playerCount: Optional[int] = 0


class NotificationFilter(FilterSchema):
    sortBy: str = "name"


class NotificationResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    players: Optional[List[dict]] = []



class NotificationListResponse(BaseSchema):
    data: List[NotificationItem] = []
