"""Validation helpers for Meta's native Reels scheduling window."""
from __future__ import annotations

from datetime import datetime


META_SCHEDULE_MIN_LEAD_SECONDS = 10 * 60
META_SCHEDULE_MAX_LEAD_SECONDS = 29 * 24 * 60 * 60


class MetaScheduleTimeError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def parse_meta_schedule_time(value, *, now_ts=None) -> int:
    """Parse a local/ISO datetime or Unix timestamp and enforce Meta's window."""
    import time

    if isinstance(value, bool) or value in (None, ""):
        raise MetaScheduleTimeError("invalid_schedule_time", "Choose a valid Meta publish time.")
    try:
        if isinstance(value, (int, float)):
            timestamp = int(value)
        else:
            raw = str(value).strip()
            try:
                timestamp = int(raw)
            except ValueError:
                parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                timestamp = int(parsed.timestamp())
    except (TypeError, ValueError, OverflowError):
        raise MetaScheduleTimeError("invalid_schedule_time", "Choose a valid Meta publish time.") from None

    now = int(time.time() if now_ts is None else now_ts)
    lead = timestamp - now
    if lead <= META_SCHEDULE_MIN_LEAD_SECONDS:
        raise MetaScheduleTimeError(
            "meta_schedule_too_soon",
            "Meta scheduled Reels must be set more than 10 minutes in advance.",
        )
    if lead > META_SCHEDULE_MAX_LEAD_SECONDS:
        raise MetaScheduleTimeError(
            "meta_schedule_too_far",
            "Meta scheduled Reels must be within the next 29 days.",
        )
    return timestamp
