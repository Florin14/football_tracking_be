from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from constants.card_type import CardType
from constants.notification_type import NotificationType
from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.match.models import MatchModel, CardModel
from modules.match.models.card_schemas import CardAdd, CardResponse
from modules.notifications.services.notification_service import create_player_notifications
from modules.team.models import TeamModel
from project_helpers.dependencies import GetInstanceFromPath, JwtRequired
from .router import router


@router.post("/{id}/cards", response_model=CardResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def add_card(
    data: CardAdd,
    match: MatchModel = Depends(GetInstanceFromPath(MatchModel)),
    db: Session = Depends(get_db),
):
    from modules.player.models.player_model import PlayerModel

    player = db.query(PlayerModel).filter(PlayerModel.id == data.playerId).first()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player with ID {data.playerId} not found"
        )

    team = db.query(TeamModel).filter(TeamModel.id == data.teamId).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID {data.teamId} not found"
        )

    if data.teamId not in [match.team1Id, match.team2Id]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Team {team.name} is not participating in this match"
        )

    if player.teamId != data.teamId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Player {player.name} does not belong to team {team.name}"
        )

    try:
        card_type = CardType(data.cardType)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid card type: {data.cardType}. Must be YELLOW or RED"
        )

    card = CardModel(
        matchId=match.id,
        playerId=data.playerId,
        teamId=data.teamId,
        cardType=card_type,
        minute=data.minute,
    )
    db.add(card)

    # Card notification for the player
    is_yellow = card_type == CardType.YELLOW
    notification_type = NotificationType.YELLOW_CARD if is_yellow else NotificationType.RED_CARD
    name_key = "notification.yellowCard" if is_yellow else "notification.redCard"
    create_player_notifications(
        db, [data.playerId],
        name_key,
        "",
        notification_type,
        params={
            "player": player.name,
            "minute": str(data.minute or "?"),
            "matchId": match.id,
        },
    )

    db.commit()
    db.refresh(card)

    return card
