"""Versioned, reversible schema migrations (additive only).

Each migration has an id, an `up` and a `down`. Applied ids are recorded in `schema_migrations`.
Rules: new tables and new nullable / defaulted columns only; existing columns are never dropped, renamed or
retyped and no rows are deleted. `down` removes only what that migration added.

* At startup the app runs every pending migration, after taking a consistent copy of the SQLite database
  (redecor.db.pre-migrate-<time>.bak) when anything is pending.
* Operators use tools/migrate.py (status / up / down) which runs the full verified backup (tools/backup.py) first.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Connection, inspect, text

from .db import Base, _sqlite_path, engine, ensure_columns, sqlite_backup

log = logging.getLogger("redecor.migrations")

# Tables that existed before versioned migrations (batch 1). Created by migration 0001 when missing.
BASELINE_TABLES = (
    "users", "images", "projects", "project_images", "clients", "site_images", "offices", "enquiries",
    "audit_log", "analytics_daily", "testimonials", "site_documents",
)


@dataclass(frozen=True)
class Migration:
    id: str
    description: str
    up: Callable[[Connection], None]
    down: Callable[[Connection], None]
    columns: tuple[tuple[str, str], ...] = ()  # (table, column) owned by this migration


def _add_column(conn: Connection, table: str, column: str) -> None:
    if column in {c["name"] for c in inspect(conn).get_columns(table)}:
        return
    col = Base.metadata.tables[table].c[column]
    ddl = f'ALTER TABLE "{table}" ADD COLUMN "{column}" {col.type.compile(conn.dialect)}'
    if col.server_default is not None and isinstance(col.server_default.arg, str):
        ddl += f" DEFAULT '{col.server_default.arg}'"
    conn.execute(text(ddl))


def _drop_column(conn: Connection, table: str, column: str) -> None:
    insp = inspect(conn)
    if column not in {c["name"] for c in insp.get_columns(table)}:
        return
    for idx in insp.get_indexes(table):
        if column in idx["column_names"]:
            conn.execute(text(f'DROP INDEX IF EXISTS "{idx["name"]}"'))
    conn.execute(text(f'ALTER TABLE "{table}" DROP COLUMN "{column}"'))


def _create_index(conn: Connection, table: str, column: str) -> None:
    for idx in Base.metadata.tables[table].indexes:
        if [c.name for c in idx.columns] == [column]:
            idx.create(conn, checkfirst=True)


def _create_tables(conn: Connection, *names: str) -> None:
    Base.metadata.create_all(conn, tables=[Base.metadata.tables[n] for n in names], checkfirst=True)


def _drop_tables(conn: Connection, *names: str) -> None:
    for n in reversed(names):
        Base.metadata.tables[n].drop(conn, checkfirst=True)


def _columns_migration(mid: str, description: str, cols: tuple[tuple[str, str], ...], indexed: tuple[tuple[str, str], ...] = (),
                       after_up: Callable[[Connection], None] | None = None) -> Migration:
    def up(conn: Connection) -> None:
        for t, c in cols:
            _add_column(conn, t, c)
        for t, c in indexed:
            _create_index(conn, t, c)
        if after_up:
            after_up(conn)

    def down(conn: Connection) -> None:
        for t, c in reversed(cols):
            _drop_column(conn, t, c)

    return Migration(mid, description, up, down, cols)


# ---------------- the migrations ----------------
def _0001_up(conn: Connection) -> None:
    _create_tables(conn, *BASELINE_TABLES)


def _0001_down(conn: Connection) -> None:
    raise RuntimeError("0001 is the baseline: it cannot be downgraded (that would delete the site's data)")


_M0002_COLS = (
    ("images", "sha256"),
    ("project_images", "kind"),
    ("project_images", "focal_x"),
    ("project_images", "focal_y"),
    ("project_images", "alt_en"),
    ("project_images", "alt_ar"),
    ("project_images", "quality_warnings"),
    ("project_images", "quality_override_by"),
    ("project_images", "quality_override_at"),
)


def _0002_backfill(conn: Connection) -> None:
    # Only a recorded fact is carried over: images already flagged as renders get kind="render".
    # Everything else stays empty until an admin sets it (no guessing "executed").
    conn.execute(text("UPDATE project_images SET kind = 'render' WHERE is_render = 1 AND kind IS NULL"))


_M0004_COLS = (("enquiries", "assigned_to_id"), ("enquiries", "next_follow_up"), ("enquiries", "source_page"))


def _0004_up(conn: Connection) -> None:
    for t, c in _M0004_COLS:
        _add_column(conn, t, c)
    for t, c in (("enquiries", "assigned_to_id"), ("enquiries", "next_follow_up")):
        _create_index(conn, t, c)
    _create_tables(conn, "enquiry_events", "enquiry_attachments", "job_runs")


def _0004_down(conn: Connection) -> None:
    _drop_tables(conn, "enquiry_events", "enquiry_attachments", "job_runs")
    for t, c in reversed(_M0004_COLS):
        _drop_column(conn, t, c)


MIGRATIONS: list[Migration] = [
    Migration("0001_baseline", "Tables of the first release (created only when missing)", _0001_up, _0001_down),
    _columns_migration("0002_media_quality", "Image hash, render/executed kind, focal point, alt text, quality override",
                       _M0002_COLS, indexed=(("images", "sha256"),), after_up=_0002_backfill),
    Migration("0003_approvals", "Append-only approvals register",
              lambda c: _create_tables(c, "approvals"), lambda c: _drop_tables(c, "approvals")),
    Migration("0004_crm_attachments", "Enquiry CRM fields, history, attachments, scheduled job state",
              _0004_up, _0004_down, _M0004_COLS),
    Migration("0005_import_log", "Import audit log",
              lambda c: _create_tables(c, "import_log"), lambda c: _drop_tables(c, "import_log")),
]
OWNED_COLUMNS = {tc for m in MIGRATIONS for tc in m.columns}


def _ensure_table(conn: Connection) -> None:
    conn.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (id VARCHAR(60) PRIMARY KEY, applied_at VARCHAR(40))"))


def applied() -> list[str]:
    with engine.begin() as conn:
        _ensure_table(conn)
        return [r[0] for r in conn.execute(text("SELECT id FROM schema_migrations ORDER BY id"))]


def pending() -> list[Migration]:
    done = set(applied())
    return [m for m in MIGRATIONS if m.id not in done]


def backup_before(reason: str) -> str | None:
    """Consistent copy of the SQLite file next to it. Returns the path (verified non-empty) or None."""
    db_file = _sqlite_path()
    if not db_file or not db_file.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = sqlite_backup(db_file.with_name(f"{db_file.name}.{reason}-{stamp}.bak"))
    if dest.stat().st_size == 0:
        raise RuntimeError(f"Backup {dest} is empty: refusing to migrate")
    return str(dest)


def upgrade(target: str | None = None, backup: bool = True) -> list[str]:
    """Apply pending migrations (up to `target`). Returns the applied ids."""
    todo = pending()
    if target:
        todo = [m for m in todo if m.id <= target]
    if not todo:
        return []
    if backup:
        path = backup_before("pre-migrate")
        if path:
            log.info("Database backed up before migrating: %s", path)
    done = []
    for m in todo:
        with engine.begin() as conn:
            _ensure_table(conn)
            m.up(conn)
            conn.execute(text("INSERT INTO schema_migrations (id, applied_at) VALUES (:i, :t)"),
                         {"i": m.id, "t": datetime.now().isoformat(timespec="seconds")})
        if m.id == "0001_baseline":
            # columns added in the first release after its tables existed (forward-only, owned columns excluded)
            ensure_columns(tables=BASELINE_TABLES, skip=OWNED_COLUMNS)
        done.append(m.id)
        log.info("Migration applied: %s (%s)", m.id, m.description)
    return done


def downgrade(steps: int = 1, backup: bool = True) -> list[str]:
    """Revert the newest `steps` applied migrations (never the baseline)."""
    done = applied()
    victims = [m for m in reversed(MIGRATIONS) if m.id in done][:steps]
    if any(m.id == "0001_baseline" for m in victims):
        raise RuntimeError("Refusing to downgrade the baseline migration")
    if victims and backup:
        backup_before("pre-downgrade")
    reverted = []
    for m in victims:
        with engine.begin() as conn:
            m.down(conn)
            conn.execute(text("DELETE FROM schema_migrations WHERE id = :i"), {"i": m.id})
        reverted.append(m.id)
        log.info("Migration reverted: %s", m.id)
    return reverted
