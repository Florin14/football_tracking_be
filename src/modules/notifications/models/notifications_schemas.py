from typing import List, Optional

from pydantic import Field, validator

from project_helpers.schemas import BaseSchema, FilterSchema, PaginationParams


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


class NotificationListParams(PaginationParams):
    search: Optional[str] = None


class NotificationResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    players: Optional[List[dict]] = []



class NotificationListResponse(BaseSchema):
    data: List[NotificationItem] = []
