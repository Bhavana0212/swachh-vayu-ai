"""Small shared helpers: text cleaning and time formatting."""
from __future__ import annotations

import re
from datetime import datetime

_WS = re.compile(r"\s+")


def clean_text(text: str | None, max_len: int = 300) -> str:
    """Collapse whitespace, trim and cap length. Returns "" for blank input."""
    if not text:
        return ""
    cleaned = _WS.sub(" ", str(text)).strip()
    return cleaned[:max_len]


def hour_label(iso_time: str | int) -> str:
    """'2026-11-21T14:00' -> '2 PM'; also accepts an hour int (14 -> '2 PM').

    Falls back to the raw value for anything else.
    """
    if isinstance(iso_time, int):
        hour = iso_time % 24
    else:
        try:
            dt = datetime.fromisoformat(iso_time)
        except (ValueError, TypeError):
            return str(iso_time)
        hour = dt.hour
    if hour == 0:
        return "12 AM"
    if hour < 12:
        return f"{hour} AM"
    if hour == 12:
        return "12 PM"
    return f"{hour - 12} PM"


def day_label(iso_time: str) -> str:
    """'2026-11-21T14:00' -> 'Sat 21 Nov'. Falls back to the raw value."""
    try:
        dt = datetime.fromisoformat(iso_time)
    except ValueError:
        return iso_time
    return dt.strftime("%a %d %b")


def safe_float(value, default: float | None = None) -> float | None:
    """Best-effort float conversion; returns default on failure."""
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default
