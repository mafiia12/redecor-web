"""Import projects from .xlsx, .csv (UTF-8) or the JSON portfolio manifest. DRY-RUN by default.

    python tools/import_projects.py --file projects.xlsx                          # dry-run: every row, every bad cell
    python tools/import_projects.py --file tools/portfolio_manifest.json          # the 59-project manifest
    python tools/import_projects.py --file projects.xlsx --apply --as you@company.com
    python tools/import_projects.py --template project-import-template.xlsx       # write the empty template

New projects are always created UNPUBLISHED. Existing projects (same slug) are skipped unless
--update-existing is given; then only the filled cells change. --apply takes a full verified backup
(tools/backup.py) first and writes an entry in the import log. See docs/CONTENT_GUIDE.md.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "tools"))


def print_rows(rows) -> None:
    for r in rows:
        detail = "; ".join(r.errors or r.notes)
        print(f"row {r.row:>4}  {r.action:<6}  {r.slug[:40]:<40}  {detail}")
    counts = {a: sum(r.action == a for r in rows) for a in ("create", "update", "skip", "error")}
    print(f"\n{len(rows)} rows: {counts['create']} create, {counts['update']} update, {counts['skip']} skip, {counts['error']} error")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file")
    ap.add_argument("--template", help="write the empty Excel template to this path and exit")
    ap.add_argument("--update-existing", action="store_true", help="change existing projects (same slug)")
    ap.add_argument("--apply", action="store_true", help="really import (default: dry-run)")
    ap.add_argument("--as", dest="user", help="admin/editor e-mail recorded in the audit log (required with --apply)")
    ap.add_argument("--backup-dir", default=str(ROOT / "backups"))
    a = ap.parse_args()

    from app import importer

    if a.template:
        Path(a.template).write_bytes(importer.template_xlsx())
        print(f"Template written: {a.template}")
        return 0
    if not a.file:
        ap.error("--file is required")

    from sqlalchemy import select

    import app.models  # noqa: F401
    from app.db import SessionLocal
    from app.models import User

    path = Path(a.file)
    rows = importer.read(path.name, path.read_bytes())
    with SessionLocal() as db:
        if not a.apply:
            print_rows(importer.plan(db, rows, a.update_existing))
            print("\nDRY-RUN: nothing was written. Add --apply --as <email> to execute.")
            return 0
        user = db.scalar(select(User).where(User.email == (a.user or "").lower()))
        if not user or user.role not in ("admin", "editor"):
            sys.exit("--as must be an existing admin or editor account")
        from migrate import full_backup

        full_backup(a.backup_dir)
        planned, _ = importer.apply(db, rows, user, a.update_existing, filename=f"CLI {path.name}")
        print_rows(planned)
        print("\nAPPLIED (new projects are unpublished).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
