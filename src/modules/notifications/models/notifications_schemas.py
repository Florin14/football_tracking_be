from datetime import datetime
from typing import List, Optional

from pydantic import AliasChoices, Field

from project_helpers.schemas import BaseSchema, FilterSchema, PaginationParams


class NotificationAdd(BaseSchema):
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    userId: int = Field(..., validation_alias=AliasChoices("userId", "playerId"))
    type: Optional[str] = "NEW_MATCH"
    createdAt: Optional[datetime] = None


class NotificationUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=200)


class NotificationItem(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    isDeleted: bool = False
    createdAt: Optional[datetime] = None
    type: Optional[str] = None


class NotificationFilter(FilterSchema):
    sortBy: str = "name"


class NotificationListParams(PaginationParams):
    search: Optional[str] = None


class NotificationResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    userId: int
    type: Optional[str] = None
    createdAt: Optional[datetime] = None


class NotificationListResponse(BaseSchema):
    data: List[NotificationItem] = []

