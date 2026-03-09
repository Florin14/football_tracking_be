import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import joinedload

from constants.match_state import MatchState
from constants.notification_type import NotificationType
from extensions.sqlalchemy import SessionLocal
from modules.match.models.match_model import MatchModel
from modules.notifications.models.notifications_model import NotificationModel
from modules.notifications.services.notification_service import create_player_notifications
from modules.player.models.player_model import PlayerModel
from modules.team.models.team_model import TeamModel
from project_helpers.emails_handling.send_emails_function import (
    SendEmailRequest,
    build_message,
    send_via_gmail_oauth2_safe,
    validate_config,
    _get_base_camp_logo,
    FRONTEND_URL,
)

logger = logging.getLogger(__name__)


def _get_reminder_subject_and_datetime(match, lang: str):
    fmt_datetime = match.timestamp.strftime("%d.%m.%Y, %H:%M")
    subject = f"Reminder: {match.team1.name} vs {match.team2.name}"
    return subject, fmt_datetime


async def _send_reminder_emails(db, match, recipients: list[str], lang: str = "ro"):
    if not recipients:
        return

    try:
        validate_config()
    except RuntimeError as exc:
        logger.warning("Reminder email not sent for match %s: %s", match.id, exc)
        return

    import base64
    base_camp_logo = _get_base_camp_logo(db)
    team1_logo = base64.b64encode(match.team1.logo).decode("utf-8") if match.team1.logo else None
    team2_logo = base64.b64encode(match.team2.logo).decode("utf-8") if match.team2.logo else None
    match_url = f"{FRONTEND_URL}/matches/{match.id}"

    subject, fmt_datetime = _get_reminder_subject_and_datetime(match, lang)

    if lang == "en":
        title = "Match Reminder"
        message = "Your match is coming up in less than 2 days!"
    else:
        title = "Reminder Meci"
        message = "Meciul tau este in mai putin de 2 zile!"

    template_data = {
        "lang": lang,
        "title": title,
        "message": message,
        "team1_name": match.team1.name,
        "team2_name": match.team2.name,
        "team1_logo": team1_logo,
        "team2_logo": team2_logo,
        "match_datetime": fmt_datetime,
        "location": match.location or ("TBD" if lang == "en" else "De stabilit"),
        "league_name": match.league.name if match.league else ("TBD" if lang == "en" else "De stabilit"),
        "round": match.round,
        "match_url": match_url,
        "base_camp_logo": base_camp_logo,
        "platform_url": FRONTEND_URL,
    }
    email_req = SendEmailRequest(to=sorted(recipients), subject=subject)
    msg = build_message(email_req, template_data=template_data)
    await send_via_gmail_oauth2_safe(msg)


def _already_reminded(db, match_id: int) -> bool:
    """Check if a MATCH_REMINDER notification was already sent for this match."""
    existing = (
        db.query(NotificationModel.id)
        .filter(
            NotificationModel.type == NotificationType.MATCH_REMINDER,
            NotificationModel.description.contains(f'"matchId": {match_id}'),
        )
        .first()
    )
    return existing is not None


def run_match_reminder_job():
    """Scheduled job: sends reminder email + notification 2 days before base camp matches."""
    logger.info("Running match reminder job...")
    db = SessionLocal()
    try:
        default_team = db.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()
        if not default_team:
            logger.info("No default (base camp) team found, skipping reminders.")
            return

        now = datetime.utcnow()
        reminder_window_end = now + timedelta(days=2)

        upcoming_matches = (
            db.query(MatchModel)
            .options(
                joinedload(MatchModel.team1),
                joinedload(MatchModel.team2),
                joinedload(MatchModel.league),
            )
            .filter(
                MatchModel.state == MatchState.SCHEDULED,
                MatchModel.timestamp > now,
                MatchModel.timestamp <= reminder_window_end,
                (MatchModel.team1Id == default_team.id) | (MatchModel.team2Id == default_team.id),
            )
            .all()
        )

        if not upcoming_matches:
            logger.info("No upcoming base camp matches within 2 days.")
            return

        for match in upcoming_matches:
            if _already_reminded(db, match.id):
                logger.info("Reminder already sent for match %s, skipping.", match.id)
                continue

            # Get base camp player emails (respecting receiveMatchReminders preference)
            from modules.player.models.player_preferences_model import PlayerPreferencesModel

            player_rows = (
                db.query(PlayerModel.id, PlayerModel.email)
                .outerjoin(PlayerPreferencesModel, PlayerPreferencesModel.playerId == PlayerModel.id)
                .filter(
                    PlayerModel.teamId == default_team.id,
                    PlayerModel.email.isnot(None),
                    (PlayerPreferencesModel.receiveMatchReminders.is_(True) | PlayerPreferencesModel.id.is_(None)),
                )
                .all()
            )

            player_ids = [pid for pid, _ in player_rows]
            recipients = [
                email for _, email in player_rows
                if email and not email.endswith("@generated.local")
            ]

            # Create in-app notifications
            create_player_notifications(
                db,
                player_ids,
                "notification.matchReminder",
                "",
                NotificationType.MATCH_REMINDER,
                params={
                    "team1": match.team1.name,
                    "team2": match.team2.name,
                    "matchId": match.id,
                    "location": match.location or "",
                    "date": match.timestamp.strftime("%d.%m.%Y %H:%M"),
                },
            )
            db.commit()

            # Send emails (APScheduler runs in a thread, so create a new event loop)
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    _send_reminder_emails(db, match, recipients, lang="ro")
                )
            finally:
                loop.close()
            logger.info("Reminder sent for match %s (%s vs %s).", match.id, match.team1.name, match.team2.name)

    except Exception:
        logger.exception("Error in match reminder job")
        db.rollback()
    finally:
        db.close()
