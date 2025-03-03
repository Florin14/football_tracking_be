class MatchAdd(BaseSchema):
    location: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    cor: str = Field(..., min_length=1)
    availablePositions: int = Field(..., min_length=1)
    employerId: int = Field(..., min_length=1)


class MatchUpdate(BaseSchema):
    location: Optional[str] = Field(None, min_length=1)
    name: Optional[str] = Field(None, min_length=1)
    cor: Optional[str] = Field(None, min_length=1)
    availablePositions: Optional[int] = None
    ocuppiedPositions: Optional[int] = None


class MatchFilter(FilterSchema):
    pass