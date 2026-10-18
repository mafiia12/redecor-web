from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

_is_sqlite = settings.database_url.startswith("sqlite")
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=True,
)

if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def _sqlite_path() -> Path | None:
    if not _is_sqlite:
        return None
    raw = settings.database_url.split("sqlite:///", 1)[-1]
    return Path(raw).resolve() if raw and raw != ":memory:" else None


def sqlite_backup(dest: Path) -> Path:
    """Consistent copy of the live SQLite database (safe with WAL and open connections)."""
    import sqlite3

    src = _sqlite_path()
    if not src or not src.exists():
        raise FileNotFoundError("No SQLite database file to back up")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(src) as s, sqlite3.connect(dest) as d:
        s.backup(d)
    return dest


def ensure_columns() -> list[str]:
    """Forward-only migration: add columns/indexes that exist in the models but not yet in the database.
    Never drops or rewrites data. Before the first change on SQLite, a copy of the database is saved next to it
    (redecor.db.pre-migrate-YYYYmmdd-HHMMSS.bak) so the step can be rolled back by restoring that file."""
    from datetime import datetime

    from sqlalchemy import inspect, text

    insp = inspect(engine)
    todo: list[tuple[str, str]] = []
    for table in Base.metadata.sorted_tables:
        if not insp.has_table(table.name):
            continue
        have = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name in have:
                continue
            ddl = f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {col.type.compile(engine.dialect)}'
            if col.server_default is not None and isinstance(col.server_default.arg, str):
                ddl += f" DEFAULT '{col.server_default.arg}'"
            elif not col.nullable:
                ddl += " DEFAULT 0"
            todo.append((f"{table.name}.{col.name}", ddl))
    if todo:
        db_file = _sqlite_path()
        if db_file and db_file.exists():
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            sqlite_backup(db_file.with_name(f"{db_file.name}.pre-migrate-{stamp}.bak"))
        with engine.begin() as conn:
            for _, ddl in todo:
                conn.execute(text(ddl))
    for table in Base.metadata.sorted_tables:  # indexes for columns added above (create_all skips existing tables)
        for idx in table.indexes:
            idx.create(engine, checkfirst=True)
    return [name for name, _ in todo]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
