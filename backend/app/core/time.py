"""UTC time helpers (PRD 5.4). Store UTC with microsecond precision; never naive datetimes."""

from datetime import UTC, datetime


class NaiveDatetimeError(ValueError):
    """Raised when a timezone-naive datetime reaches a boundary that requires UTC."""


def utcnow() -> datetime:
    """Current time as an aware UTC datetime (microsecond precision)."""
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    """Convert an aware datetime to UTC. Naive datetimes are rejected, not guessed."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise NaiveDatetimeError(f"naive datetime not allowed: {value!r}")
    return value.astimezone(UTC)


def parse_utc(value: str) -> datetime:
    """Parse an ISO-8601 timestamp with offset (or `Z`) into UTC."""
    return ensure_utc(datetime.fromisoformat(value))


def to_iso(value: datetime) -> str:
    """ISO-8601 UTC with microseconds and a `Z` suffix, e.g. 2026-10-03T14:00:00.000000Z."""
    return ensure_utc(value).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
