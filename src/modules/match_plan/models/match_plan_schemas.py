import json
from datetime import datetime
from typing import List, Optional

from pydantic import Field, model_validator

from project_helpers.schemas import BaseSchema


class MatchPlanSave(BaseSchema):
    matchDate: Optional[datetime] = Field(None, example="2024-12-25T15:00:00")
    location: Optional[str] = Field(None, example="Stadium Arena")
    formation: str = Field("2-2-1", example="2-2-1")
    opponentName: Optional[str] = Field(None, example="Nordic Lions")
    opponentNotes: Optional[str] = Field(None, example="Strong midfield")
    playerIds: List[int] = Field(default_factory=list, example=[1, 2, 3])


class MatchPlanResponse(BaseSchema):
    id: int
    matchDate: Optional[datetime] = None
    location: Optional[str] = None
    formation: str = "2-2-1"
    opponentName: Optional[str] = None
    opponentNotes: Optional[str] = None
    playerIds: List[int] = []

    @model_validator(mode="before")
    @classmethod
    def deserialize_player_ids(cls, values):
        obj = values
        if hasattr(obj, "playerIds"):
            raw = obj.playerIds
        elif isinstance(obj, dict):
            raw = obj.get("playerIds")
        else:
            return values

        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                parsed = []
            if hasattr(obj, "__dict__"):
                # SQLAlchemy model — build a dict instead
                d = {
                    "id": obj.id,
                    "matchDate": obj.matchDate,
                    "location": obj.location,
                    "formation": obj.formation,
                    "opponentName": obj.opponentName,
                    "opponentNotes": obj.opponentNotes,
                    "playerIds": parsed,
                }
                return d
            else:
                obj["playerIds"] = parsed
        return values
