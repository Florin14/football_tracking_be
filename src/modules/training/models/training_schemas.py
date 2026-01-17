from datetime import datetime
from typing import List, Optional

from pydantic import Field

from project_helpers.schemas import BaseSchema


class TrainingSessionAdd(BaseSchema):
    timestamp: datetime = Field(..., example="2024-12-25T15:00:00")
    location: Optional[str] = Field(None, example="Stadium Arena")
    details: Optional[str] = Field(None, example="Recovery session")


class TrainingSessionUpdate(BaseSchema):
    timestamp: Optional[datetime] = Field(None, example="2024-12-25T15:00:00")
    location: Optional[str] = Field(None, example="Stadium Arena")
    details: Optional[str] = Field(None, example="Recovery session")


class TrainingSessionResponse(BaseSchema):
    id: int
    timestamp: datetime
    location: Optional[str] = None
    details: Optional[str] = None


class TrainingSessionListResponse(BaseSchema):
    data: List[TrainingSessionResponse] = []
