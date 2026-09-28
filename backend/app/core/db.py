"""Declarative base, base model (id + created_at), engine and session factory."""

from collections.abc import Iterator
from datetime import datetime
from functools import lru_cache

from sqlalchemy import Engine, MetaData, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.core.config import get_settings
from app.core.ids import new_ulid
from app.core.time import utcnow
from app.core.types import ULIDType, UTCDateTime

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {datetime: UTCDateTime()}  # noqa: RUF012 - SQLAlchemy API


class BaseModel(Base):
    """Every table: ULID `id` and `created_at` (PRD 14.5)."""

    __abstract__ = True

    id: Mapped[str] = mapped_column(ULIDType, primary_key=True, default=new_ulid)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utcnow, server_default=func.now()
    )


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, committed by the caller."""
    with get_sessionmaker()() as session:
        yield session
