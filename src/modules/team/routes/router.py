from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.team.models import TeamModel, TeamAdd, TeamUpdate, TeamResponse, TeamListResponse, AddPlayerToTeam
from modules.player.models import PlayerModel
from project_helpers.responses import ConfirmationResponse


router = APIRouter(prefix='/teams', tags=['Team'])
