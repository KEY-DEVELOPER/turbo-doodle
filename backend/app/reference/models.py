"""Reference data (PRD 5.2, 14.5): sport-agnostic spine plus external-ID mapping."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.bitemporal import BitemporalMixin, bitemporal_table_args
from app.core.db import BaseModel
from app.core.types import ULIDType, UTCDateTime


class Sport(BaseModel):
    __tablename__ = "sport"

    code: Mapped[str] = mapped_column(String(32), unique=True)  # e.g. "football"
    name: Mapped[str] = mapped_column(Text)


class CompetitionKind(StrEnum):
    LEAGUE = "league"
    CUP = "cup"
    OTHER = "other"


class Competition(BaseModel):
    __tablename__ = "competition"
    __table_args__ = (CheckConstraint("kind IN ('league', 'cup', 'other')", name="kind"),)

    sport_id: Mapped[str] = mapped_column(ULIDType, ForeignKey("sport.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)  # e.g. "ita-serie-a"
    name: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(16))
    country_code: Mapped[str | None] = mapped_column(String(8))  # ISO 3166 (or e.g. "EU")
    tier: Mapped[int | None] = mapped_column(Integer)


class Season(BaseModel):
    __tablename__ = "season"
    __table_args__ = (
        UniqueConstraint("competition_id", "label"),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="date_range"),
    )

    competition_id: Mapped[str] = mapped_column(ULIDType, ForeignKey("competition.id"))
    label: Mapped[str] = mapped_column(String(32))  # e.g. "2026/27"
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)


class Venue(BaseModel):
    __tablename__ = "venue"

    name: Mapped[str] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    country_code: Mapped[str | None] = mapped_column(String(8))


class TeamCategory(StrEnum):
    """Men's, women's, youth and reserve sides are distinct teams (PRD 5.2)."""

    SENIOR_MEN = "senior_men"
    SENIOR_WOMEN = "senior_women"
    YOUTH = "youth"
    RESERVE = "reserve"
    OTHER = "other"


class Team(BaseModel):
    """A participant. Named `team` per PRD; sport-agnostic via `sport_id`."""

    __tablename__ = "team"
    __table_args__ = (
        CheckConstraint(
            "category IN ('senior_men', 'senior_women', 'youth', 'reserve', 'other')",
            name="category",
        ),
    )

    sport_id: Mapped[str] = mapped_column(ULIDType, ForeignKey("sport.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    short_name: Mapped[str | None] = mapped_column(Text)
    country_code: Mapped[str | None] = mapped_column(String(8))
    category: Mapped[str] = mapped_column(String(16))
    home_venue_id: Mapped[str | None] = mapped_column(ULIDType, ForeignKey("venue.id"))


class TeamAlias(BitemporalMixin, BaseModel):
    """Curated alias; renames add a row with validity dates rather than a new team."""

    __tablename__ = "team_alias"
    __bitemporal_key__ = ("team_id", "alias", "lang", "source_id")
    __table_args__ = bitemporal_table_args(__tablename__, __bitemporal_key__)

    team_id: Mapped[str] = mapped_column(ULIDType, ForeignKey("team.id"), index=True)
    alias: Mapped[str] = mapped_column(Text)
    lang: Mapped[str | None] = mapped_column(String(8))
    source_id: Mapped[str | None] = mapped_column(ULIDType, ForeignKey("source.id"))
    correction_reason: Mapped[str | None] = mapped_column(Text)


class Bookmaker(BaseModel):
    """Brand, licence entity and regional site are stored separately (PRD 5.2)."""

    __tablename__ = "bookmaker"

    code: Mapped[str] = mapped_column(String(64), unique=True)
    brand: Mapped[str] = mapped_column(Text)
    licence_entity: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(String(16))
    site_domain: Mapped[str | None] = mapped_column(Text)


class BookmakerRuleset(BaseModel):
    """Versioned, manually curated settlement rules (A-12, PRD 4.7). New rules = new version."""

    __tablename__ = "bookmaker_ruleset"
    __table_args__ = (
        UniqueConstraint("bookmaker_id", "version"),
        CheckConstraint("version >= 1", name="version_positive"),
    )

    bookmaker_id: Mapped[str] = mapped_column(ULIDType, ForeignKey("bookmaker.id"))
    version: Mapped[int] = mapped_column(Integer)
    effective_from: Mapped[datetime] = mapped_column(UTCDateTime())
    void_policy_class: Mapped[str] = mapped_column(String(128))
    rules: Mapped[dict[str, Any]] = mapped_column(JSONB)
    source_url: Mapped[str] = mapped_column(Text)
    reviewed_by: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class EntityType(StrEnum):
    SPORT = "sport"
    COMPETITION = "competition"
    SEASON = "season"
    TEAM = "team"
    VENUE = "venue"
    EVENT = "event"
    BOOKMAKER = "bookmaker"
    MARKET = "market"
    SELECTION = "selection"


class SourceEntityMap(BitemporalMixin, BaseModel):
    """External ID -> canonical ULID. The only place external IDs live (CLAUDE.md 5)."""

    __tablename__ = "source_entity_map"
    __bitemporal_key__ = ("source_id", "entity_type", "external_id")
    __table_args__ = (
        *bitemporal_table_args(__tablename__, __bitemporal_key__),
        CheckConstraint(
            "entity_type IN ('sport', 'competition', 'season', 'team', 'venue', 'event', "
            "'bookmaker', 'market', 'selection')",
            name="entity_type",
        ),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
    )

    source_id: Mapped[str] = mapped_column(ULIDType, ForeignKey("source.id"))
    entity_type: Mapped[str] = mapped_column(String(32))
    external_id: Mapped[str] = mapped_column(Text)
    canonical_id: Mapped[str] = mapped_column(ULIDType, index=True)
    method: Mapped[str] = mapped_column(String(32))  # e.g. exact, curated, review
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    reviewed_by: Mapped[str | None] = mapped_column(Text)
    correction_reason: Mapped[str | None] = mapped_column(Text)
