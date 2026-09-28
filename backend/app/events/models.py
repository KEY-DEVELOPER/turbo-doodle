"""Events (matches) and their append-only status/kickoff history (PRD 5.2, 14.5).

`event` holds the current state; every change also appends a history row. Rescheduling keeps
the same `event_id` and appends to `kickoff_history`.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import BaseModel
from app.core.types import ULIDType, UTCDateTime


class EventStatus(StrEnum):
    SCHEDULED = "scheduled"
    POSTPONED = "postponed"
    RESCHEDULED = "rescheduled"
    ABANDONED = "abandoned"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    AWARDED = "awarded"
    PLAYED = "played"


EVENT_STATUS_CHECK = "status IN ({})".format(", ".join(f"'{s.value}'" for s in EventStatus))


class Event(BaseModel):
    __tablename__ = "event"
    __table_args__ = (
        CheckConstraint(EVENT_STATUS_CHECK, name="status"),
        CheckConstraint("home_team_id <> away_team_id", name="distinct_teams"),
        Index("ix_event_season_id_scheduled_kickoff", "season_id", "scheduled_kickoff"),
    )

    season_id: Mapped[str] = mapped_column(ULIDType, ForeignKey("season.id"))
    home_team_id: Mapped[str] = mapped_column(ULIDType, ForeignKey("team.id"), index=True)
    away_team_id: Mapped[str] = mapped_column(ULIDType, ForeignKey("team.id"), index=True)
    venue_id: Mapped[str | None] = mapped_column(ULIDType, ForeignKey("venue.id"))
    neutral_venue: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    neutral_venue_inferred: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )
    scheduled_kickoff: Mapped[datetime] = mapped_column(UTCDateTime())  # event_time
    status: Mapped[str] = mapped_column(String(16), default=EventStatus.SCHEDULED.value)
    stage: Mapped[str | None] = mapped_column(Text)
    round: Mapped[str | None] = mapped_column(Text)
    duplicate_of_id: Mapped[str | None] = mapped_column(ULIDType, ForeignKey("event.id"))


class EventStatusHistory(BaseModel):
    """Append-only (DB trigger)."""

    __tablename__ = "event_status_history"
    __table_args__ = (CheckConstraint(EVENT_STATUS_CHECK, name="status"),)

    event_id: Mapped[str] = mapped_column(ULIDType, ForeignKey("event.id"), index=True)
    status: Mapped[str] = mapped_column(String(16))
    previous_status: Mapped[str | None] = mapped_column(String(16))
    source_id: Mapped[str | None] = mapped_column(ULIDType, ForeignKey("source.id"))
    source_time: Mapped[datetime | None] = mapped_column(UTCDateTime())
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime())
    reason: Mapped[str | None] = mapped_column(Text)


class KickoffHistory(BaseModel):
    """Append-only (DB trigger)."""

    __tablename__ = "kickoff_history"

    event_id: Mapped[str] = mapped_column(ULIDType, ForeignKey("event.id"), index=True)
    scheduled_kickoff: Mapped[datetime] = mapped_column(UTCDateTime())
    previous_kickoff: Mapped[datetime | None] = mapped_column(UTCDateTime())
    source_id: Mapped[str | None] = mapped_column(ULIDType, ForeignKey("source.id"))
    source_time: Mapped[datetime | None] = mapped_column(UTCDateTime())
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime())
    reason: Mapped[str | None] = mapped_column(Text)
