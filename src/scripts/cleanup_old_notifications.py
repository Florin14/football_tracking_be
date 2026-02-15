"""
Cleanup old notifications older than 30 days.

Usage:
    cd football_tracking_be/src
    python -m scripts.cleanup_old_notifications

Cron example:
    0 3 * * * cd /path/to/src && python -m scripts.cleanup_old_notifications
"""
import logging
from datetime import datetime, timedelta

from extensions.sqlalchemy import SessionLocal
from modules.notifications.models.notifications_model import NotificationModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RETENTION_DAYS = 30


def cleanup():
    cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    db = SessionLocal()
    try:
        count = (
            db.query(NotificationModel)
            .filter(NotificationModel.createdAt < cutoff)
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info("Deleted %d notifications older than %s", count, cutoff.isoformat())
    except Exception:
        db.rollback()
        logger.exception("Failed to cleanup notifications")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    cleanup()
