from typing import List, Optional

from pydantic import AliasChoices, Field, validator

from modules.player.models.player_schemas import PlayerResponse
from project_helpers.functions import process_and_convert_image_to_base64
from project_helpers.schemas import BaseSchema, FilterSchema, PaginationParams


class TeamAdd(BaseSchema):
    name: str = Field(..., max_length=50, example="Base Camp")
    description: Optional[str] = Field(None, max_length=200, example="Professional football team")
    logo: Optional[bytes] = Field(None)
    leagueId: int = Field(..., example=1)

    @validator("logo", pre=False, always=True)
    def encode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, (bytes, bytearray)) and len(value) == 0:
            return None
        if isinstance(value, str) and value == "":
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
        if isinstance(value, (bytes, bytearray)) and len(value) == 0:
            return None
        if isinstance(value, str) and value == "":
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
    points: Optional[int] = 0
    goalsFor: Optional[int] = 0
    goalsAgainst: Optional[int] = 0
    wins: Optional[int] = 0
    draws: Optional[int] = 0
    losses: Optional[int] = 0

    @validator("logo", pre=False, always=True)
    def decode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value


class TeamFilter(FilterSchema):
    sortBy: str = "name"


class TeamListParams(PaginationParams):
    search: Optional[str] = None
    leagueId: Optional[int] = Field(None, validation_alias=AliasChoices("leagueId", "league_id"))
    excludeLeagueId: Optional[int] = Field(
        None, validation_alias=AliasChoices("excludeLeagueId", "exclude_league_id")
    )
    tournamentId: Optional[int] = Field(None, validation_alias=AliasChoices("tournamentId", "tournament_id"))
    excludeTournamentId: Optional[int] = Field(
        None, validation_alias=AliasChoices("excludeTournamentId", "exclude_tournament_id")
    )


class TeamResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    players: Optional[List[PlayerResponse]] = []
    logo: Optional[str] = Field(None, example="")

    @validator("logo", pre=False, always=True)
    def decode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value


class BaseCampTeamResponse(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None
    players: Optional[List[PlayerResponse]] = []
    logo: Optional[str] = Field(None, example="")

    @validator("logo", pre=False, always=True)
    def decode_image_from_base64(cls, value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value


class TeamListResponse(BaseSchema):
    data: List[TeamItem] = []


class PlayerStatItem(BaseSchema):
    playerId: int
    playerName: str
    value: int


class BaseCampStatsResponse(BaseSchema):
    topScorer: Optional[PlayerStatItem] = None
    topAssists: Optional[PlayerStatItem] = None
    topAppearances: Optional[PlayerStatItem] = None
