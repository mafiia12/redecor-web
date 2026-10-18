"""One-file backup of the site data: the database and every uploaded photo.

    python tools/backup.py                      # local dev: reads backend/redecor.db and backend/uploads
    python tools/backup.py --db /data/redecor.db --uploads /data/uploads --out backup.zip

Restore on the new server: unzip it so that redecor.db and uploads/ land where DATABASE_URL / UPLOAD_DIR point.
"""
import argparse
import time
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent / "backend"
ap = argparse.ArgumentParser()
ap.add_argument("--db", default=str(root / "redecor.db"))
ap.add_argument("--uploads", default=str(root / "uploads"))
ap.add_argument("--out", default=f"redecor-backup-{time.strftime('%Y%m%d-%H%M')}.zip")
a = ap.parse_args()

with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED) as z:
    db = Path(a.db)
    if db.exists():
        z.write(db, "redecor.db")
    n = 0
    for f in Path(a.uploads).rglob("*"):
        if f.is_file():
            z.write(f, Path("uploads") / f.relative_to(a.uploads))
            n += 1
print(f"Saved {a.out}  (database: {'yes' if Path(a.db).exists() else 'NOT FOUND'}, {n} files)")
