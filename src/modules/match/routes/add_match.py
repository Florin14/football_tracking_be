from fastapi import BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel, MatchAdd, MatchResponse
)
from modules.team.models.team_model import TeamModel
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.league_team_model import LeagueTeamModel
from project_helpers.emails_handling import send_match_notification_emails, get_admin_lang
from constants.notification_type import NotificationType
from modules.notifications.services.notification_service import create_player_notifications
from project_helpers.dependencies import JwtRequired
from .router import router


@router.post("/", response_model=MatchResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def add_match(
    data: MatchAdd,
    request: Request,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
):
    from modules.player.models.player_model import PlayerModel

    if data.team1Id == data.team2Id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A team cannot play against itself"
        )

    team_ids = {data.team1Id, data.team2Id}
    teams = db.query(TeamModel).filter(TeamModel.id.in_(team_ids)).all()
    if len(teams) != 2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more teams not found",
        )

    league_id = data.leagueId
    if data.friendly:
        league_id = None
    elif league_id:
        league = db.query(LeagueModel).filter(LeagueModel.id == league_id).first()
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"League with ID {league_id} not found",
            )
        membership = (
            db.query(LeagueTeamModel)
            .filter(
                LeagueTeamModel.leagueId == league_id,
                LeagueTeamModel.teamId.in_(team_ids),
            )
            .all()
        )
        if len(membership) != 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both teams must belong to the selected league",
            )
    else:
        league_ids = (
            db.query(LeagueTeamModel.leagueId)
            .filter(LeagueTeamModel.teamId == data.team1Id)
            .all()
        )
        league_ids_1 = {league_id for (league_id,) in league_ids}
        league_ids = (
            db.query(LeagueTeamModel.leagueId)
            .filter(LeagueTeamModel.teamId == data.team2Id)
            .all()
        )
        league_ids_2 = {league_id for (league_id,) in league_ids}
        common = league_ids_1.intersection(league_ids_2)
        if len(common) == 1:
            league_id = next(iter(common))
        elif len(common) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Teams do not share a league. Provide leagueId.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Teams share multiple leagues. Provide leagueId.",
            )

    if data.round is not None and not league_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Round can only be set for league matches",
        )

    match = MatchModel(
        team1Id=data.team1Id,
        team2Id=data.team2Id,
        location=data.location,
        timestamp=data.timestamp,
        leagueId=league_id,
        round=data.round,
        youtubeUrl=data.youtubeUrl,
    )

    db.add(match)
    db.commit()

    match = (
        db.query(MatchModel)
        .options(
            joinedload(MatchModel.team1),
            joinedload(MatchModel.team2),
            joinedload(MatchModel.league),
        )
        .filter(MatchModel.id == match.id)
        .first()
    )

    recipient_rows = (
        db.query(PlayerModel.email)
        .filter(
            PlayerModel.teamId.in_(team_ids),
            PlayerModel.email.isnot(None),
        )
        .all()
    )

    recipients = [
        email for (email,) in recipient_rows
        if email and not email.endswith("@generated.local")
    ]

    admin_lang = get_admin_lang(db, request.state.user)
    tenant = getattr(request.state, "tenant", None)
    tenant_name = tenant.name if tenant else None
    send_match_notification_emails(bg, db, match, recipients, lang=admin_lang, tenant_name=tenant_name)

    # Create NEW_MATCH notifications for default team players
    default_team = db.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()
    if default_team and default_team.id in team_ids:
        default_player_ids = [
            pid for (pid,) in db.query(PlayerModel.id)
            .filter(PlayerModel.teamId == default_team.id)
            .all()
        ]
        create_player_notifications(
            db,
            default_player_ids,
            "notification.newMatch",
            "",
            NotificationType.NEW_MATCH,
            params={
                "team1": match.team1.name,
                "team2": match.team2.name,
                "matchId": match.id,
                "location": match.location or "",
                "date": match.timestamp.strftime("%Y-%m-%d %H:%M"),
            },
        )
        db.commit()

    return match
