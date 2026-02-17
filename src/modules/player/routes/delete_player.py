from fastapi import Depends
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions import get_db
from modules.match.models.goal_model import GoalModel
from modules.player.models.player_model import PlayerModel
from project_helpers.dependencies import GetInstanceFromPath, JwtRequired
from project_helpers.responses import ConfirmationResponse
from .router import router


@router.delete("/{id:int}", response_model=ConfirmationResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def delete_player(
    player: PlayerModel = Depends(GetInstanceFromPath(PlayerModel)),
    db: Session = Depends(get_db),
):
    """Delete a player"""
    player_id = player.id
    player_name = player.name

    # Keep goal history but detach the foreign key to allow player deletion.
    db.query(GoalModel).filter(GoalModel.playerId == player_id).update(
        {
            GoalModel.playerId: None,
            GoalModel.playerNameSnapshot: player_name,
        },
        synchronize_session=False,
    )
    db.query(GoalModel).filter(GoalModel.assistPlayerId == player_id).update(
        {
            GoalModel.assistPlayerId: None,
            GoalModel.assistPlayerNameSnapshot: player_name,
        },
        synchronize_session=False,
    )

    # Delete the player (joined-inheritance row + base user row).
    # Related rows are handled by DB-level ON DELETE rules.
    db.delete(player)
    db.commit()

    return ConfirmationResponse(
        message=f"Player {player_name} deleted successfully"
    )
