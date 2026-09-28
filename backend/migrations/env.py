"""Alembic environment. URL precedence: config attribute `connection` (tests) >
`-x url=...` > EDGELEDGER_DATABASE_URL."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, create_engine

from app.all_models import __all__ as _registered  # noqa: F401 - populates metadata
from app.core.config import get_settings
from app.core.db import Base
from migrations.autogen import COMPARE_OPTS

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _url() -> str:
    return context.get_x_argument(as_dictionary=True).get("url") or get_settings().database_url


def _run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, **COMPARE_OPTS)
    with context.begin_transaction():
        context.run_migrations()


def run_offline() -> None:
    context.configure(
        url=_url(), target_metadata=target_metadata, literal_binds=True, **COMPARE_OPTS
    )
    with context.begin_transaction():
        context.run_migrations()


def run_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return
    engine = create_engine(_url())
    with engine.connect() as conn:
        _run(conn)
        conn.commit()
    engine.dispose()


if context.is_offline_mode():
    run_offline()
else:
    run_online()
