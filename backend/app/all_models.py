"""Imports every module's ORM models so `Base.metadata` is complete (Alembic, tests).

When your module adds `models.py`, add one import line here.
"""

from app.audit import models as audit_models
from app.events import models as events_models
from app.markets import models as markets_models
from app.reference import models as reference_models
from app.sources import models as sources_models

__all__ = [
    "audit_models",
    "events_models",
    "markets_models",
    "reference_models",
    "sources_models",
]
