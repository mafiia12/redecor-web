"""Database migrations for operators.

    python tools/migrate.py status
    python tools/migrate.py up                 # full verified backup first, then all pending migrations
    python tools/migrate.py down --steps 1     # full verified backup first, then revert the newest migration

Reads DATABASE_URL / UPLOAD_DIR / ATTACHMENTS_DIR like the app (backend/.env is loaded automatically).
The backup is made with tools/backup.py and must exist and be non-empty, otherwise nothing is changed.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "tools"))


def full_backup(out_dir: str) -> Path:
    import backup as bk
    from app.config import settings

    db = settings.database_url.split("sqlite:///", 1)[1] if settings.database_url.startswith("sqlite") else settings.database_url
    args = argparse.Namespace(db=db, uploads=str(settings.upload_dir), attachments=str(settings.attachments_dir),
                              out_dir=out_dir, keep=10_000, copy_to="")
    path = bk.run_once(args)
    if not path.exists() or path.stat().st_size == 0:
        raise SystemExit(f"Backup {path} missing or empty: aborting")
    print(f"backup ok: {path} ({path.stat().st_size} bytes)")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["status", "up", "down"])
    ap.add_argument("--steps", type=int, default=1)
    ap.add_argument("--backup-dir", default=str(ROOT / "backups"))
    ap.add_argument("--no-backup", action="store_true", help="only for throw-away test databases")
    a = ap.parse_args()

    import app.models  # noqa: F401  (register tables)
    from app import migrations

    if a.action == "status":
        done = set(migrations.applied())
        for m in migrations.MIGRATIONS:
            print(f"{'applied ' if m.id in done else 'PENDING '} {m.id}  {m.description}")
        return 0
    if not a.no_backup:
        full_backup(a.backup_dir)
    if a.action == "up":
        print("applied:", ", ".join(migrations.upgrade(backup=False)) or "nothing pending")
    else:
        print("reverted:", ", ".join(migrations.downgrade(steps=a.steps, backup=False)) or "nothing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
