from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.core.time import NaiveDatetimeError, ensure_utc, parse_utc, to_iso, utcnow


def test_utcnow_is_aware_utc() -> None:
    now = utcnow()
    assert now.tzinfo is UTC


def test_ensure_utc_converts_offsets() -> None:
    rome = timezone(timedelta(hours=2))
    assert ensure_utc(datetime(2026, 10, 3, 16, 0, tzinfo=rome)) == datetime(
        2026, 10, 3, 14, 0, tzinfo=UTC
    )


def test_ensure_utc_rejects_naive() -> None:
    with pytest.raises(NaiveDatetimeError):
        ensure_utc(datetime(2026, 10, 3, 14, 0))  # noqa: DTZ001 - deliberately naive


def test_to_iso_keeps_microseconds_and_z() -> None:
    value = datetime(2026, 10, 3, 14, 0, 0, 5, tzinfo=UTC)
    assert to_iso(value) == "2026-10-03T14:00:00.000005Z"


def test_parse_utc() -> None:
    assert parse_utc("2026-10-03T16:00:00+02:00") == datetime(2026, 10, 3, 14, tzinfo=UTC)
    assert parse_utc("2026-10-03T14:00:00Z") == datetime(2026, 10, 3, 14, tzinfo=UTC)
    with pytest.raises(NaiveDatetimeError):
        parse_utc("2026-10-03T14:00:00")
