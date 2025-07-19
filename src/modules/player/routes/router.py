# Created by: cicada
# Date: Mon 02/03/2025
# Time: 14:11:47.00

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.player.models import (
    PlayerModel, PlayerAdd, PlayerUpdate, PlayerResponse, PlayerListResponse
)
from modules.team.models import TeamModel
from constants.player_positions import PlayerPositions
from constants.platform_roles import PlatformRoles
from project_helpers.responses import ConfirmationResponse
from project_helpers.functions.generate_password import hash_password


router = APIRouter(prefix='/players', tags=['Player'])
