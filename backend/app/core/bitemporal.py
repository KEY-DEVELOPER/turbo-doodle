"""Bitemporal (system-time) versioning for curated facts (PRD 5.4, 5.5).

A bitemporal table keeps every version of a fact. The current version has `valid_to IS NULL`.
A correction never edits a version: it closes the current row (`valid_to = at`) and inserts a
new row (`valid_from = at`). The database backs this up with:

- a partial unique index on the business key `WHERE valid_to IS NULL` (one current version);
- a guard trigger (see `app.core.ddl`) that only allows `valid_to` to go from NULL to a value.

Usage in a model::

    class TeamAlias(BitemporalMixin, BaseModel):
        __tablename__ = "team_alias"
        __bitemporal_key__ = ("team_id", "alias", "lang", "source_id")
        __table_args__ = bitemporal_table_args("team_alias", __bitemporal_key__)
"""

from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import CheckConstraint, ColumnElement, Index, and_, or_, select, text
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.time import ensure_utc, utcnow
from app.core.types import UTCDateTime

_SYSTEM_COLUMNS = frozenset({"id", "created_at", "valid_from", "valid_to"})


class BitemporalError(Exception):
    pass


class BitemporalMixin:
    __bitemporal_key__: ClassVar[tuple[str, ...]]

    valid_from: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, default=utcnow)
    valid_to: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


def bitemporal_table_args(table: str, key: tuple[str, ...]) -> tuple[Any, ...]:
    """Constraints every bitemporal table needs: valid range + one current row per key."""
    return (
        CheckConstraint("valid_to IS NULL OR valid_to > valid_from", name="valid_range"),
        Index(
            f"uq_{table}_current",
            *key,
            unique=True,
            postgresql_where=text("valid_to IS NULL"),
            postgresql_nulls_not_distinct=True,
        ),
    )


def is_current(model: type[BitemporalMixin]) -> ColumnElement[bool]:
    return model.valid_to.is_(None)


def as_of(model: type[BitemporalMixin], at: datetime) -> ColumnElement[bool]:
    """Filter for the version that was current (as known by us) at system time `at`."""
    at = ensure_utc(at)
    return and_(model.valid_from <= at, or_(model.valid_to.is_(None), model.valid_to > at))


def _lock_current[T: BitemporalMixin](session: Session, row: T) -> T:
    model = type(row)
    pk = row.id  # type: ignore[attr-defined]
    locked = session.execute(
        select(model).where(model.id == pk).with_for_update()  # type: ignore[attr-defined]
    ).scalar_one()
    if locked.valid_to is not None:
        raise BitemporalError(f"{model.__name__} {pk} is already closed")
    return locked


def close[T: BitemporalMixin](session: Session, row: T, at: datetime | None = None) -> T:
    """End the current version without a successor (e.g. an alias stops being valid)."""
    at = ensure_utc(at or utcnow())
    current = _lock_current(session, row)
    if at <= current.valid_from:
        raise BitemporalError("valid_to must be after valid_from")
    current.valid_to = at
    session.flush()
    return current


def supersede[T: BitemporalMixin](
    session: Session, row: T, changes: dict[str, Any], at: datetime | None = None
) -> T:
    """Close `row` at `at` and insert its successor with `changes` applied.

    Business-key columns cannot change (that would be a different fact, not a correction).
    Returns the new current row.
    """
    model = type(row)
    bad = set(changes) & (set(model.__bitemporal_key__) | _SYSTEM_COLUMNS)
    if bad:
        raise BitemporalError(f"cannot change key/system columns via supersede: {sorted(bad)}")
    at = ensure_utc(at or utcnow())
    current = close(session, row, at)
    values = {
        attr.key: getattr(current, attr.key)
        for attr in model.__mapper__.column_attrs  # type: ignore[attr-defined]
        if attr.key not in _SYSTEM_COLUMNS
    }
    values.update(changes)
    values["valid_from"] = at
    successor = model(**values)
    session.add(successor)
    session.flush()
    return successor
