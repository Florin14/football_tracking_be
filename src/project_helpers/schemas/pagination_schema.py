from pydantic import AliasChoices, Field

from .base_schema import BaseSchema


class PaginationParams(BaseSchema):
    skip: int = Field(0, ge=0, validation_alias=AliasChoices("skip", "offset"))
    limit: int = Field(100, ge=1, validation_alias=AliasChoices("limit", "pageSize"))

    def apply(self, query):
        return query.offset(self.skip).limit(self.limit)
