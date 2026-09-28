"""ULID generation (PRD 5.2): 48-bit ms timestamp + 80-bit randomness, Crockford base32.

IDs are stored as `CHAR(26) COLLATE "C"` so byte order equals time order. Generation is
monotonic within a process: IDs created in the same millisecond increment the random part,
so `sorted(ids) == ids` for IDs generated in sequence.
"""

import secrets
import threading
import time
from datetime import UTC, datetime

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_DECODE = {c: i for i, c in enumerate(ALPHABET)}
ULID_LENGTH = 26
_MAX_RANDOM = (1 << 80) - 1
_MAX_TIMESTAMP_MS = (1 << 48) - 1

_lock = threading.Lock()
_last_ms = -1
_last_random = 0


def _encode(value: int) -> str:
    chars = []
    for _ in range(ULID_LENGTH):
        chars.append(ALPHABET[value & 0x1F])
        value >>= 5
    return "".join(reversed(chars))


def new_ulid(at: datetime | None = None) -> str:
    """Return a new ULID string. `at` pins the timestamp part (non-monotonic; for backfills)."""
    global _last_ms, _last_random  # noqa: PLW0603 - process-wide monotonic state
    if at is not None:
        ms = int(at.timestamp() * 1000)
        return _encode((ms << 80) | secrets.randbits(80))
    with _lock:
        ms = time.time_ns() // 1_000_000
        if ms <= _last_ms:
            # Same (or clock went back) millisecond: keep order by incrementing.
            ms = _last_ms
            if _last_random == _MAX_RANDOM:
                ms += 1
                _last_random = secrets.randbits(80)
            else:
                _last_random += 1
        else:
            _last_random = secrets.randbits(80)
        _last_ms = ms
        if ms > _MAX_TIMESTAMP_MS:
            raise OverflowError("ULID timestamp overflow")
        return _encode((ms << 80) | _last_random)


def is_ulid(value: str) -> bool:
    return (
        len(value) == ULID_LENGTH
        and all(c in _DECODE for c in value)
        and _DECODE[value[0]] <= 7  # 26*5 = 130 bits; top 2 bits must be zero
    )


def ulid_timestamp(value: str) -> datetime:
    """Return the UTC creation time embedded in a ULID."""
    if not is_ulid(value):
        raise ValueError(f"not a ULID: {value!r}")
    n = 0
    for c in value:
        n = (n << 5) | _DECODE[c]
    return datetime.fromtimestamp((n >> 80) / 1000, tz=UTC)
