import os
import logging
import httpx

logger = logging.getLogger(__name__)

FUSIONBOARD_WEBHOOK_URL = os.getenv("FUSIONBOARD_WEBHOOK_URL", "http://localhost:8000/webhooks/football")
FUSIONBOARD_WEBHOOK_SECRET = os.getenv("FUSIONBOARD_WEBHOOK_SECRET", "fusionboard-webhook-secret-2026")


async def send_webhook(event_type: str, data: dict):
    """
    Send a webhook notification to FusionBoard.
    Runs async, failures are logged but don't affect the main operation.
    """
    payload = {
        "event": event_type,
        "data": data,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                FUSIONBOARD_WEBHOOK_URL,
                json=payload,
                headers={
                    "X-Webhook-Secret": FUSIONBOARD_WEBHOOK_SECRET,
                    "Content-Type": "application/json",
                },
            )
            if response.status_code == 200:
                logger.info(f"Webhook sent: {event_type}")
            else:
                logger.warning(f"Webhook response {response.status_code} for {event_type}")
    except Exception as e:
        logger.warning(f"Webhook failed for {event_type}: {e}")


def send_webhook_background(event_type: str, data: dict):
    """
    Wrapper for use with FastAPI BackgroundTasks.
    Since BackgroundTasks can run async functions directly in modern FastAPI,
    we return the coroutine.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(send_webhook(event_type, data))
        else:
            loop.run_until_complete(send_webhook(event_type, data))
    except RuntimeError:
        asyncio.run(send_webhook(event_type, data))
