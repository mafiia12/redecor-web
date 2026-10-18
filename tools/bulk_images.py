"""Bulk-attach project photos from a folder. DRY-RUN by default: prints the plan, writes nothing.

    python tools/bulk_images.py --dir D:\\Renders\\batch1                       # dry-run table
    python tools/bulk_images.py --dir D:\\Renders\\batch1 --mapping map.csv     # CSV overrides the file names
    python tools/bulk_images.py --dir D:\\Renders\\batch1 --apply --as you@company.com

Naming: <project-slug>__<nn>__<render|executed>[__cover].<jpg|png|webp>  (see docs/CONTENT_GUIDE.md).
--apply takes a full verified backup (tools/backup.py) first, then adds only the "create" rows.
Runs against the database in DATABASE_URL / backend/.env (stop nothing: the site can keep running).
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "tools"))


def print_table(rows) -> None:
    cols = ["file", "project", "order", "kind", "cover", "quality", "action", "reason"]
    data = [[str(getattr(r, c) if getattr(r, c) is not None else "") for c in cols] for r in rows]
    widths = [min(40, max(len(c), *(len(d[i]) for d in data))) for i, c in enumerate(cols)] if data else [len(c) for c in cols]
    line = lambda vals: "  ".join(v[:w].ljust(w) for v, w in zip(vals, widths, strict=True))  # noqa: E731
    print(line(cols))
    print(line(["-" * w for w in widths]))
    for d in data:
        print(line(d))
    counts = {a: sum(r.action == a for r in rows) for a in ("create", "skip-duplicate", "reject")}
    print(f"\n{len(rows)} files: {counts['create']} create, {counts['skip-duplicate']} skip-duplicate, {counts['reject']} reject")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--mapping", help="CSV: filename,project_slug,order,kind,is_cover,alt_en,alt_ar")
    ap.add_argument("--override-quality", action="store_true", help="accept below-standard images (recorded)")
    ap.add_argument("--apply", action="store_true", help="really add the images (default: dry-run)")
    ap.add_argument("--as", dest="user", help="admin/editor e-mail recorded as the uploader (required with --apply)")
    ap.add_argument("--backup-dir", default=str(ROOT / "backups"))
    a = ap.parse_args()

    from sqlalchemy import select

    import app.models  # noqa: F401
    from app import bulk
    from app.db import SessionLocal
    from app.models import User

    folder = Path(a.dir)
    files = [(f.name, f.read_bytes()) for f in sorted(folder.iterdir()) if f.is_file() and f.suffix.lower() in bulk.IMAGE_EXT]
    mapping = bulk.read_mapping(Path(a.mapping).read_bytes()) if a.mapping else {}
    with SessionLocal() as db:
        if not a.apply:
            print_table(bulk.plan(db, files, mapping, a.override_quality))
            print("\nDRY-RUN: nothing was written. Add --apply --as <email> to execute.")
            return 0
        user = db.scalar(select(User).where(User.email == (a.user or "").lower()))
        if not user or user.role not in ("admin", "editor"):
            sys.exit("--as must be an existing admin or editor account")
        from migrate import full_backup

        full_backup(a.backup_dir)
        rows, _ = bulk.apply(db, files, user, mapping, a.override_quality, filename=f"CLI {folder.name}")
        print_table(rows)
        print("\nAPPLIED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
