"""Database-level guards shared by migrations (append-only, bitemporal, monthly partitions).

The functions are created once in the schema-spine migration. Later migrations attach them
to their own tables with the helpers below, e.g. in `upgrade()`:

    for stmt in append_only_triggers("odds_snapshot"):
        op.execute(stmt)
"""

from datetime import date

from sqlalchemy import Connection, text

FUNCTIONS_SQL = [
    # Append-only tables: any UPDATE/DELETE/TRUNCATE is an error (raw payloads, snapshots,
    # predictions, evaluations, signals, ledger entries, audit log - CLAUDE.md 5).
    """
    CREATE OR REPLACE FUNCTION edgeledger_forbid_mutation() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
      RAISE EXCEPTION 'APPEND_ONLY_VIOLATION: % on %.% is not allowed',
        TG_OP, TG_TABLE_SCHEMA, TG_TABLE_NAME
        USING ERRCODE = 'restrict_violation';
    END;
    $$;
    """,
    # Bitemporal tables: DELETE forbidden; UPDATE may only set valid_to from NULL.
    """
    CREATE OR REPLACE FUNCTION edgeledger_bitemporal_guard() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'BITEMPORAL_VIOLATION: DELETE on % is not allowed', TG_TABLE_NAME
          USING ERRCODE = 'restrict_violation';
      END IF;
      IF OLD.valid_to IS NOT NULL
         OR NEW.valid_to IS NULL
         OR (to_jsonb(OLD) - 'valid_to') <> (to_jsonb(NEW) - 'valid_to') THEN
        RAISE EXCEPTION 'BITEMPORAL_VIOLATION: only closing valid_to is allowed on %',
          TG_TABLE_NAME USING ERRCODE = 'restrict_violation';
      END IF;
      RETURN NEW;
    END;
    $$;
    """,
    # Monthly RANGE partitions named <parent>_yYYYYmMM. Idempotent.
    """
    CREATE OR REPLACE FUNCTION edgeledger_ensure_monthly_partitions(
      parent text, from_month date, months integer
    ) RETURNS void
    LANGUAGE plpgsql AS $$
    DECLARE
      m date := date_trunc('month', from_month)::date;
      i integer;
    BEGIN
      FOR i IN 0..months - 1 LOOP
        EXECUTE format(
          'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
          parent || '_y' || to_char(m, 'YYYY') || 'm' || to_char(m, 'MM'),
          parent,
          (m::timestamp AT TIME ZONE 'UTC'),
          ((m + interval '1 month')::timestamp AT TIME ZONE 'UTC')
        );
        m := (m + interval '1 month')::date;
      END LOOP;
    END;
    $$;
    """,
]

DROP_FUNCTIONS_SQL = [
    "DROP FUNCTION IF EXISTS edgeledger_ensure_monthly_partitions(text, date, integer)",
    "DROP FUNCTION IF EXISTS edgeledger_bitemporal_guard()",
    "DROP FUNCTION IF EXISTS edgeledger_forbid_mutation()",
]

# Regex (Python `re`) matching partition child tables, so autogenerate ignores them.
PARTITION_NAME_PATTERN = r"^[a-z_]+_y\d{4}m\d{2}$"


def append_only_triggers(table: str) -> list[str]:
    """Triggers + revokes making `table` insert-only (works on partitioned parents)."""
    return [
        f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
        "FOR EACH ROW EXECUTE FUNCTION edgeledger_forbid_mutation()",
        f"CREATE TRIGGER {table}_no_truncate BEFORE TRUNCATE ON {table} "
        "FOR EACH STATEMENT EXECUTE FUNCTION edgeledger_forbid_mutation()",
        f"REVOKE UPDATE, DELETE, TRUNCATE ON {table} FROM PUBLIC",
    ]


def bitemporal_triggers(table: str) -> list[str]:
    return [
        f"CREATE TRIGGER {table}_bitemporal_guard BEFORE UPDATE OR DELETE ON {table} "
        "FOR EACH ROW EXECUTE FUNCTION edgeledger_bitemporal_guard()",
        f"CREATE TRIGGER {table}_no_truncate BEFORE TRUNCATE ON {table} "
        "FOR EACH STATEMENT EXECUTE FUNCTION edgeledger_forbid_mutation()",
    ]


def ensure_monthly_partitions(conn: Connection, parent: str, from_month: date, months: int) -> None:
    """Create missing monthly partitions; for a scheduled maintenance job."""
    conn.execute(
        text("SELECT edgeledger_ensure_monthly_partitions(:p, :f, :n)"),
        {"p": parent, "f": from_month, "n": months},
    )
