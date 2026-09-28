from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.core.bitemporal import BitemporalError, as_of, close, is_current, supersede
from app.core.ids import new_ulid
from app.reference.models import SourceEntityMap
from app.sources.models import Source

T0 = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
T1 = T0 + timedelta(days=1)
T2 = T0 + timedelta(days=2)


def _source(session: Session) -> Source:
    src = Source(
        code=f"fixture-{new_ulid()}",
        name="Recorded fixture source",
        kind="historical_import",
        licence_ref="TEST-ONLY",
        permitted_display=False,
        permitted_store=True,
        retain_after_termination=False,
        permitted_train=False,
        permitted_derived=False,
    )
    session.add(src)
    session.flush()
    return src


def _mapping(session: Session) -> SourceEntityMap:
    row = SourceEntityMap(
        source_id=_source(session).id,
        entity_type="team",
        external_id="ext-42",
        canonical_id=new_ulid(),
        method="exact",
        confidence=Decimal("1"),
        valid_from=T0,
    )
    session.add(row)
    session.flush()
    return row


@pytest.mark.db
def test_supersede_closes_old_row_and_opens_new_one(db_session: Session) -> None:
    old = _mapping(db_session)
    new_canonical = new_ulid()

    new = supersede(
        db_session, old, {"canonical_id": new_canonical, "correction_reason": "wrong team"}, at=T1
    )

    db_session.refresh(old)
    assert old.valid_to == T1
    assert new.id != old.id
    assert new.valid_from == T1
    assert new.valid_to is None
    assert new.canonical_id == new_canonical
    assert (new.source_id, new.entity_type, new.external_id) == (
        old.source_id,
        old.entity_type,
        old.external_id,
    )

    key = SourceEntityMap.external_id == "ext-42"
    current = db_session.scalars(select(SourceEntityMap).where(key, is_current(SourceEntityMap)))
    assert [r.id for r in current] == [new.id]
    before = db_session.scalars(select(SourceEntityMap).where(key, as_of(SourceEntityMap, T0)))
    assert [r.id for r in before] == [old.id]
    after = db_session.scalars(select(SourceEntityMap).where(key, as_of(SourceEntityMap, T2)))
    assert [r.id for r in after] == [new.id]


@pytest.mark.db
def test_supersede_rejects_key_changes_and_closed_rows(db_session: Session) -> None:
    old = _mapping(db_session)
    with pytest.raises(BitemporalError):
        supersede(db_session, old, {"external_id": "other"}, at=T1)
    with pytest.raises(BitemporalError):
        supersede(db_session, old, {"method": "curated"}, at=T0)  # not after valid_from
    close(db_session, old, at=T1)
    with pytest.raises(BitemporalError):
        supersede(db_session, old, {"method": "curated"}, at=T2)


@pytest.mark.db
def test_only_one_current_version_per_key(db_session: Session) -> None:
    old = _mapping(db_session)
    dup = SourceEntityMap(
        source_id=old.source_id,
        entity_type="team",
        external_id="ext-42",
        canonical_id=new_ulid(),
        method="exact",
        confidence=Decimal("1"),
        valid_from=T1,
    )
    with (
        pytest.raises(IntegrityError, match="uq_source_entity_map_current"),
        db_session.begin_nested(),
    ):
        db_session.add(dup)
        db_session.flush()


@pytest.mark.db
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE source_entity_map SET canonical_id = '01K6ARCH00000000000000SPRT' WHERE id = :id",
        "UPDATE source_entity_map SET valid_from = now() WHERE id = :id",
        "DELETE FROM source_entity_map WHERE id = :id",
    ],
)
def test_db_guard_blocks_history_edits(db_session: Session, statement: str) -> None:
    row = _mapping(db_session)
    with pytest.raises(DBAPIError, match="BITEMPORAL_VIOLATION"), db_session.begin_nested():
        db_session.execute(text(statement), {"id": row.id})


@pytest.mark.db
def test_db_guard_blocks_reopening_closed_row(db_session: Session) -> None:
    row = _mapping(db_session)
    close(db_session, row, at=T1)
    with pytest.raises(DBAPIError, match="BITEMPORAL_VIOLATION"), db_session.begin_nested():
        db_session.execute(
            text("UPDATE source_entity_map SET valid_to = NULL WHERE id = :id"), {"id": row.id}
        )
