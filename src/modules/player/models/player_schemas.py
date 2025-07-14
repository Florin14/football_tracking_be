from typing import List, Optional

from pydantic import Field

from project_helpers.schemas import BaseSchema, FilterSchema


class PlayerAdd(BaseSchema):
    name: str = Field(..., max_length=50, example="John Doe")
    email: str = Field(..., max_length=40, example="john.doe@example.com")
    password: str = Field(..., min_length=6, example="password123")
    position: str = Field(..., example="FORWARD")  # Should match PlayerPositions enum
    rating: Optional[int] = Field(None, ge=0, le=100, example=85)


class PlayerUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=40)
    position: Optional[str] = None
    rating: Optional[int] = Field(None, ge=0, le=100)


class PlayerItem(BaseSchema):
    id: int
    name: str
    email: str
    position: Optional[str] = None
    rating: Optional[int] = None
    teamName: Optional[str] = None


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


class PlayerListResponse(BaseSchema):
    data: List[PlayerItem] = []
