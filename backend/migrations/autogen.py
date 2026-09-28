"""Autogenerate/compare options shared by env.py and the drift test."""

import re
from typing import Any, Literal

from app.core.ddl import PARTITION_NAME_PATTERN
from app.core.types import UTCDateTime

_partition = re.compile(PARTITION_NAME_PATTERN)


def include_object(
    obj: Any, name: str | None, type_: str, reflected: bool, compare_to: Any
) -> bool:
    # Monthly partitions are created by edgeledger_ensure_monthly_partitions, not by models.
    return not (type_ == "table" and name is not None and _partition.match(name))


def render_item(type_: str, obj: Any, autogen_context: Any) -> str | Literal[False]:
    # Render app-level TypeDecorators as plain SQLAlchemy types so migrations never import app.
    if type_ == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime(timezone=True)"
    return False


COMPARE_OPTS: dict[str, Any] = {
    "include_object": include_object,
    "render_item": render_item,
    "compare_type": True,
}
