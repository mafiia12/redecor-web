"""Restore a backup made by tools/backup.py. Stop the website first.

    python tools/restore.py redecor-backup-20261018-020000.zip --db backend/redecor.db --uploads backend/uploads

Safety: the zip is verified before anything is touched; the current database and uploads folder are MOVED aside
(…before-restore-<time>) rather than deleted, so a restore can itself be undone.
"""

import argparse
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backup import log, verify_zip  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("zip")
    ap.add_argument("--db", required=True, help="where the SQLite database must end up")
    ap.add_argument("--uploads", required=True, help="where the uploads folder must end up")
    ap.add_argument("--attachments", default="", help="where the private attachments folder must end up")
    a = ap.parse_args()
    manifest = verify_zip(Path(a.zip))
    if manifest["engine"] != "sqlite":
        log("PostgreSQL backup: restore redecor.sql with psql (see docs/BACKUP_AND_RECOVERY.md)")
        return 2
    stamp = time.strftime("%Y%m%d-%H%M%S")
    db, uploads = Path(a.db), Path(a.uploads)
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(a.zip) as z:
            z.extractall(tmp)
        att = Path(a.attachments) if a.attachments else None
        for p in (db, Path(f"{db}-wal"), Path(f"{db}-shm"), uploads, *([att] if att else [])):
            if p.exists():
                aside = p.with_name(f"{p.name}.before-restore-{stamp}")
                p.rename(aside)
                log(f"moved current {p} -> {aside.name}")
        db.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(Path(tmp) / "redecor.db"), db)
        src_up = Path(tmp) / "uploads"
        if src_up.exists():
            shutil.move(str(src_up), uploads)
        else:
            uploads.mkdir(parents=True, exist_ok=True)
        src_att = Path(tmp) / "attachments"
        if att is not None:
            if src_att.exists():
                shutil.move(str(src_att), att)
            else:
                att.mkdir(parents=True, exist_ok=True)
    log(f"restored {a.zip}: {manifest['upload_files']} files. Start the website again.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
