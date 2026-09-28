"""Shared fixtures.

DB tests (`@pytest.mark.db`) run against a throwaway database created per test session on the
server in EDGELEDGER_TEST_DATABASE_URL, so parallel agents/worktrees never collide. When the
server is unreachable they are skipped locally, but fail when EDGELEDGER_REQUIRE_DB=1 (CI).
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.ids import new_ulid

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ADMIN_URL = "postgresql+psycopg://edgeledger:edgeledger@localhost:5432/postgres"


def _admin_url() -> str:
    return os.environ.get("EDGELEDGER_TEST_DATABASE_URL", DEFAULT_ADMIN_URL)


def _require_db() -> bool:
    return os.environ.get("EDGELEDGER_REQUIRE_DB") == "1"


@pytest.fixture(scope="session")
def admin_engine() -> Iterator[Engine]:
    engine = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        engine.dispose()
        if _require_db():
            raise
        pytest.skip(
            f"PostgreSQL not reachable ({exc.__class__.__name__}); set EDGELEDGER_TEST_DATABASE_URL"
        )
    yield engine
    engine.dispose()


def _create_database(admin: Engine) -> str:
    name = f"edgeledger_test_{new_ulid().lower()}"
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    return make_url(_admin_url()).set(database=name).render_as_string(hide_password=False)


def _drop_database(admin: Engine, url: str) -> None:
    name = make_url(url).database
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))


@pytest.fixture
def empty_db_url(admin_engine: Engine) -> Iterator[str]:
    """A brand-new empty database for one test (migration tests)."""
    url = _create_database(admin_engine)
    yield url
    _drop_database(admin_engine, url)


def alembic_config() -> Config:
    return Config(str(BACKEND_DIR / "alembic.ini"))


def run_alembic(conn: Connection, action: str, target: str) -> None:
    cfg = alembic_config()
    cfg.attributes["connection"] = conn
    getattr(command, action)(cfg, target)


@pytest.fixture(scope="session")
def migrated_engine(admin_engine: Engine) -> Iterator[Engine]:
    """Session-wide database migrated to head."""
    url = _create_database(admin_engine)
    engine = create_engine(url)
    with engine.begin() as conn:
        run_alembic(conn, "upgrade", "head")
    yield engine
    engine.dispose()
    _drop_database(admin_engine, url)


@pytest.fixture
def db_session(migrated_engine: Engine) -> Iterator[Session]:
    """Session inside a transaction that is rolled back after the test."""
    with migrated_engine.connect() as conn:
        trans = conn.begin()
        session = Session(bind=conn, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            trans.rollback()
