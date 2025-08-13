from typing import Literal, Optional
from pydantic import field_validator, Field
from .base_schema import BaseSchema


class FilterSchema(BaseSchema):
    search: Optional[str] = None
    offset: Optional[int] = Field(1, ge=1)
    limit: Optional[int] = None
    sortBy: Optional[str] = "id"
    sortType: Optional[Literal["asc", "desc"]] = "asc"

    @field_validator("limit")
    def recalculate_offset(cls, v, info):
        info.data["offset"] = (info.data["offset"] - 1) * (v or 1)
        return v
