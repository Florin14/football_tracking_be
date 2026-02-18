from fastapi import HTTPException, status

from constants.preferred_language import PreferredLanguage
from constants.preferred_theme import PreferredTheme


def normalize_preferred_language(value: str | None) -> PreferredLanguage | None:
    if value is None:
        return None
    raw = value.strip().upper()
    if raw in {"RO", "ROMANA", "ROMANIAN"}:
        return PreferredLanguage.RO
    if raw in {"EN", "ENGLEZA", "ENGLISH"}:
        return PreferredLanguage.EN
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid preferred language (allowed: RO or EN)",
    )


def normalize_preferred_theme(value: str | None) -> PreferredTheme | None:
    if value is None:
        return None
    raw = value.strip().upper()
    if raw in {"LIGHT"}:
        return PreferredTheme.LIGHT
    if raw in {"DARK"}:
        return PreferredTheme.DARK
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid preferred theme (allowed: LIGHT or DARK)",
    )


def apply_preferences(prefs, data) -> None:
    if data.preferredPosition is not None:
        prefs.preferredPosition = data.preferredPosition
    if data.preferredLanguage is not None:
        prefs.preferredLanguage = normalize_preferred_language(data.preferredLanguage)
    if data.preferredTheme is not None:
        prefs.preferredTheme = normalize_preferred_theme(data.preferredTheme)
    if data.nickname is not None:
        prefs.nickname = data.nickname
    if data.receiveEmailNotifications is not None:
        prefs.receiveEmailNotifications = data.receiveEmailNotifications
    if data.receiveMatchReminders is not None:
        prefs.receiveMatchReminders = data.receiveMatchReminders
