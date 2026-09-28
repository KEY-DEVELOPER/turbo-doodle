"""Audit log (PRD 14.5): append-only, monthly RANGE partitions on `at`.

UPDATE/DELETE/TRUNCATE are blocked by triggers and revoked from PUBLIC. Partitions are created
by `edgeledger_ensure_monthly_partitions` (see `app.core.ddl`); a scheduled job must keep
creating future months. `before`/`after` must be redacted by the writer (no stakes, notes).
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import BaseModel
from app.core.time import utcnow
from app.core.types import ULIDType, UTCDateTime


class ActorType(StrEnum):
    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"
    SERVICE = "service"


class AuditLog(BaseModel):
    __tablename__ = "audit_log"
    __table_args__ = (
        CheckConstraint("actor_type IN ('user', 'admin', 'system', 'service')", name="actor_type"),
        Index("ix_audit_log_target", "target_type", "target_id"),
        Index("ix_audit_log_actor_id", "actor_id"),
        {"postgresql_partition_by": "RANGE (at)"},
    )

    # Partition key must be part of the primary key: PK = (id, at).
    at: Mapped[datetime] = mapped_column(
        UTCDateTime(), primary_key=True, default=utcnow, server_default=func.now()
    )
    actor_id: Mapped[str | None] = mapped_column(ULIDType)
    actor_type: Mapped[str] = mapped_column(String(16))
    action: Mapped[str] = mapped_column(String(128))
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_id: Mapped[str | None] = mapped_column(Text)
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)
    ip_hash: Mapped[str | None] = mapped_column(String(128))
    request_id: Mapped[str | None] = mapped_column(String(64))
