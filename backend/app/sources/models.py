"""Licence register (PRD 4.6, 14.5 `source`; DATA-01).

Every connector needs a `source` row. Permitted-use flags have no defaults: whoever registers a
source must state them explicitly. A source cannot be enabled without a licence reference.
"""

from datetime import date
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, Date, String, Text, false
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import BaseModel


class SourceKind(StrEnum):
    API = "api"
    HISTORICAL_IMPORT = "historical_import"
    MANUAL = "manual"


class Source(BaseModel):
    __tablename__ = "source"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('api', 'historical_import', 'manual')",
            name="kind",
        ),
        CheckConstraint(
            "NOT enabled OR length(btrim(licence_ref)) > 0",
            name="enabled_requires_licence",
        ),
    )

    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(32))
    licence_ref: Mapped[str] = mapped_column(Text)
    terms_version: Mapped[str | None] = mapped_column(Text)
    terms_date: Mapped[date | None] = mapped_column(Date)
    permitted_display: Mapped[bool] = mapped_column(Boolean)
    permitted_store: Mapped[bool] = mapped_column(Boolean)
    retain_after_termination: Mapped[bool] = mapped_column(Boolean)
    permitted_train: Mapped[bool] = mapped_column(Boolean)
    permitted_derived: Mapped[bool] = mapped_column(Boolean)
    attribution_text: Mapped[str | None] = mapped_column(Text)
    jurisdiction_limits: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )
    review_due: Mapped[date | None] = mapped_column(Date)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
