"""Markets and selections (PRD 5.3, 14.5).

A market row is one contract on one event; quotes are comparable only when
`contract_signature` is equal. Signature computation belongs to DATA-04 (not in this file).
"""

from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import BaseModel
from app.core.types import ULIDType


class Market(BaseModel):
    __tablename__ = "market"
    __table_args__ = (UniqueConstraint("event_id", "contract_signature"),)

    event_id: Mapped[str] = mapped_column(ULIDType, ForeignKey("event.id"))
    contract_signature: Mapped[str] = mapped_column(String(256))
    market_family: Mapped[str] = mapped_column(String(64))  # e.g. MATCH_RESULT_1X2
    period: Mapped[str] = mapped_column(String(32))  # e.g. REGULATION
    line: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    line_semantics: Mapped[str | None] = mapped_column(String(16))  # WHOLE | HALF | QUARTER
    settlement_basis: Mapped[str] = mapped_column(String(32))  # e.g. GOALS
    void_policy_class: Mapped[str] = mapped_column(String(128))
    contract: Mapped[dict[str, Any]] = mapped_column(JSONB)  # full canonical definition


class Selection(BaseModel):
    __tablename__ = "selection"
    __table_args__ = (UniqueConstraint("market_id", "code"),)

    market_id: Mapped[str] = mapped_column(ULIDType, ForeignKey("market.id"))
    code: Mapped[str] = mapped_column(String(32))  # HOME / DRAW / AWAY / OVER / ...
    display_name: Mapped[str | None] = mapped_column(Text)
