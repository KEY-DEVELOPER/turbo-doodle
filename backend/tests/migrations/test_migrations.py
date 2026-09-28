"""Schema spine migration: reversible, single head, no model drift, DB guards in place."""

from datetime import UTC, date, datetime

import pytest
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.all_models import __all__ as _registered  # noqa: F401 - populates metadata
from app.audit.models import AuditLog
from app.core.db import Base
from app.core.ids import new_ulid
from app.events.models import Event, EventStatusHistory, KickoffHistory
from app.reference.models import Competition, Season, Team
from app.sources.models import Source
from migrations.autogen import COMPARE_OPTS
from tests.conftest import alembic_config, run_alembic

SPINE_TABLES = {
    "sport",
    "competition",
    "season",
    "team",
    "team_alias",
    "venue",
    "event",
    "event_status_history",
    "kickoff_history",
    "bookmaker",
    "bookmaker_ruleset",
    "market",
    "selection",
    "source",
    "source_entity_map",
    "audit_log",
}


def _user_tables(engine: Engine) -> set[str]:
    names = set(inspect(engine).get_table_names()) - {"alembic_version"}
    return {n for n in names if not n.startswith("audit_log_y")}


def _functions(engine: Engine) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT proname FROM pg_proc WHERE proname LIKE 'edgeledger_%'"))
        return {r[0] for r in rows}


def test_single_alembic_head() -> None:
    heads = ScriptDirectory.from_config(alembic_config()).get_heads()
    assert len(heads) == 1, f"multiple heads {heads}: rebase your migration (CLAUDE.md 10)"


@pytest.mark.db
def test_upgrade_downgrade_upgrade(empty_db_url: str) -> None:
    engine = create_engine(empty_db_url)
    try:
        with engine.begin() as conn:
            run_alembic(conn, "upgrade", "head")
        assert _user_tables(engine) >= SPINE_TABLES
        assert _functions(engine) == {
            "edgeledger_forbid_mutation",
            "edgeledger_bitemporal_guard",
            "edgeledger_ensure_monthly_partitions",
        }

        with engine.begin() as conn:
            run_alembic(conn, "downgrade", "base")
        assert _user_tables(engine) == set()
        assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
        assert _functions(engine) == set()

        with engine.begin() as conn:
            run_alembic(conn, "upgrade", "head")
        assert _user_tables(engine) >= SPINE_TABLES
    finally:
        engine.dispose()


@pytest.mark.db
def test_models_match_migrations(migrated_engine: Engine) -> None:
    """ORM models and migrations must not drift (same check as `alembic check`)."""
    with migrated_engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts=COMPARE_OPTS)
        diff = compare_metadata(ctx, Base.metadata)
    assert diff == []


@pytest.mark.db
def test_football_is_seeded(db_session: Session) -> None:
    assert db_session.execute(text("SELECT name FROM sport WHERE code = 'football'")).scalar_one()


@pytest.mark.db
def test_audit_log_is_monthly_partitioned(db_session: Session) -> None:
    strategy: str = db_session.execute(
        text("SELECT partstrat FROM pg_partitioned_table WHERE partrelid = 'audit_log'::regclass")
    ).scalar_one()
    assert strategy == "r"
    now = datetime.now(UTC)
    row = AuditLog(actor_type="system", action="test.partition", at=now)
    db_session.add(row)
    db_session.flush()
    partition: str = db_session.execute(
        text("SELECT tableoid::regclass::text FROM audit_log WHERE id = :id"), {"id": row.id}
    ).scalar_one()
    assert partition == f"audit_log_y{now:%Y}m{now:%m}"


@pytest.mark.db
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE audit_log SET reason = 'edited'",
        "DELETE FROM audit_log",
        "TRUNCATE audit_log",
    ],
)
def test_audit_log_is_append_only(db_session: Session, statement: str) -> None:
    db_session.add(AuditLog(actor_type="system", action="test.append_only"))
    db_session.flush()
    with pytest.raises(DBAPIError, match="APPEND_ONLY_VIOLATION"), db_session.begin_nested():
        db_session.execute(text(statement))


def _event_with_history(session: Session) -> None:
    sport_id: str = session.execute(
        text("SELECT id FROM sport WHERE code = 'football'")
    ).scalar_one()
    competition = Competition(sport_id=sport_id, code=f"c-{new_ulid()}", name="C", kind="league")
    session.add(competition)
    session.flush()
    season = Season(competition_id=competition.id, label="2026/27")
    home = Team(sport_id=sport_id, name="Team A", category="senior_men")
    away = Team(sport_id=sport_id, name="Team B", category="senior_men")
    session.add_all([season, home, away])
    session.flush()
    kickoff = datetime(2026, 10, 3, 14, tzinfo=UTC)
    event = Event(
        season_id=season.id, home_team_id=home.id, away_team_id=away.id, scheduled_kickoff=kickoff
    )
    session.add(event)
    session.flush()
    session.add_all(
        [
            EventStatusHistory(event_id=event.id, status="scheduled", observed_at=kickoff),
            KickoffHistory(event_id=event.id, scheduled_kickoff=kickoff, observed_at=kickoff),
        ]
    )
    session.flush()


@pytest.mark.db
@pytest.mark.parametrize("table", ["event_status_history", "kickoff_history"])
@pytest.mark.parametrize(
    "statement",
    ["UPDATE {table} SET reason = 'edited'", "DELETE FROM {table}", "TRUNCATE {table}"],
)
def test_history_tables_are_append_only(db_session: Session, table: str, statement: str) -> None:
    _event_with_history(db_session)
    with pytest.raises(DBAPIError, match="APPEND_ONLY_VIOLATION"), db_session.begin_nested():
        db_session.execute(text(statement.format(table=table)))


@pytest.mark.db
def test_source_cannot_be_enabled_without_licence(db_session: Session) -> None:
    source = Source(
        code="no-licence",
        name="No licence",
        kind="api",
        licence_ref=" ",
        permitted_display=False,
        permitted_store=False,
        retain_after_termination=False,
        permitted_train=False,
        permitted_derived=False,
        review_due=date(2027, 1, 1),
        enabled=True,
    )
    with pytest.raises(IntegrityError, match="enabled_requires_licence"), db_session.begin_nested():
        db_session.add(source)
        db_session.flush()
