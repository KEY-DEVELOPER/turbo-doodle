"""Column types shared by every module (CLAUDE.md 5).

- `ULIDType`: CHAR(26) with "C" collation so text order == time order.
- `UTCDateTime`: TIMESTAMPTZ; rejects naive datetimes on write, returns UTC on read.
- `OddsDecimal`: NUMERIC(8,3). Decimal odds are the only stored odds format.
- `MoneyDecimal`: NUMERIC(18,4). Never floats for money.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CHAR, DateTime, Dialect, Numeric
from sqlalchemy.types import TypeDecorator

from app.core.time import ensure_utc

ULIDType = CHAR(26, collation="C")


class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return None if value is None else ensure_utc(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        assert isinstance(value, datetime)
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)


def OddsDecimal() -> Numeric[Decimal]:  # noqa: N802 - reads like a type
    return Numeric(8, 3, asdecimal=True)


def MoneyDecimal() -> Numeric[Decimal]:  # noqa: N802 - reads like a type
    return Numeric(18, 4, asdecimal=True)
