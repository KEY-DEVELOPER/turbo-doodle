from datetime import UTC, datetime, timedelta

import pytest

from app.core.ids import ALPHABET, ULID_LENGTH, is_ulid, new_ulid, ulid_timestamp


def test_ulid_format() -> None:
    value = new_ulid()
    assert len(value) == ULID_LENGTH
    assert set(value) <= set(ALPHABET)
    assert is_ulid(value)


def test_ulids_generated_in_sequence_sort_in_generation_order() -> None:
    # Many IDs fall in the same millisecond: monotonic increment must keep order.
    ids = [new_ulid() for _ in range(20_000)]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)


def test_ulids_sort_by_timestamp() -> None:
    base = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)
    earlier = new_ulid(at=base)
    later = new_ulid(at=base + timedelta(milliseconds=1))
    assert earlier < later


def test_ulid_timestamp_roundtrip() -> None:
    at = datetime(2026, 10, 3, 14, 0, 0, 123000, tzinfo=UTC)
    assert ulid_timestamp(new_ulid(at=at)) == at


def test_ulid_timestamp_of_new_id_is_now() -> None:
    before = datetime.now(UTC) - timedelta(seconds=1)
    assert ulid_timestamp(new_ulid()) >= before


@pytest.mark.parametrize(
    "value",
    [
        "",
        "01ARZ3NDEKTSV4RRFFQ69G5FA",
        "01ARZ3NDEKTSV4RRFFQ69G5FAVX",
        "01ARZ3NDEKTSV4RRFFQ69G5FAU",
        "81ARZ3NDEKTSV4RRFFQ69G5FAV",
    ],
)
def test_is_ulid_rejects_invalid(value: str) -> None:
    assert not is_ulid(value)
