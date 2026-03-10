import os
import hmac

from fastapi import Request

from project_helpers.error import Error
from project_helpers.exceptions import ErrorException


DASHBOARD_API_KEY = os.getenv("DASHBOARD_API_KEY", "")


class ApiKeyRequired:
    """Dependency that validates the X-API-Key header against the configured secret."""

    def __call__(self, request: Request) -> None:
        api_key = request.headers.get("X-API-Key", "")
        if not DASHBOARD_API_KEY:
            raise ErrorException(
                error=Error.SERVER_ERROR,
                statusCode=500,
                message="Dashboard API key is not configured on the server.",
            )
        if not hmac.compare_digest(api_key, DASHBOARD_API_KEY):
            raise ErrorException(
                error=Error.INVALID_TOKEN,
                statusCode=403,
                message="Invalid or missing API key.",
            )
