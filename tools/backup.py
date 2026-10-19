"""Backup of the website data: database + uploaded photos/documents, verified, with retention.

    python tools/backup.py                                   # local dev (backend/redecor.db, backend/uploads)
    python tools/backup.py --out-dir D:\\Backups\\redecor --keep 30 --copy-to "\\\\nas\\share\\redecor"
    python tools/backup.py --loop-hours 24                   # stay running, one backup per day (Docker 'backup' service)

What it does, every run:
  1. copies the SQLite database with SQLite's online-backup API (consistent even while the site is running;
     PostgreSQL: uses pg_dump when DATABASE_URL is postgres and pg_dump is installed),
  2. zips it with every file under the uploads folder plus a manifest (counts + SHA-256),
  3. VERIFIES the zip: CRC of every member, and PRAGMA integrity_check on the copied database,
  4. optionally copies the zip to a second location (network share / synced cloud folder) and verifies the copy,
  5. deletes the oldest backups beyond --keep.
Exit code is non-zero on any failure; ALERT_WEBHOOK_URL (if set) receives a short failure message.
Restore with tools/restore.py (see docs/BACKUP_AND_RECOVERY.md).
"""

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "backend"


def log(msg: str) -> None:
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} backup: {msg}", flush=True)


def alert(msg: str) -> None:
    url = os.getenv("ALERT_WEBHOOK_URL", "").strip()
    if not url:
        return
    body = json.dumps({"text": f"[Redecor website] backup: {msg}", "content": f"[Redecor website] backup: {msg}"}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}), timeout=8)  # noqa: S310
    except Exception as e:  # noqa: BLE001
        log(f"alert webhook failed: {type(e).__name__}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def default_db() -> str:
    url = os.getenv("DATABASE_URL", "")
    if url.startswith("sqlite:///"):
        return url.split("sqlite:///", 1)[1]
    if url.startswith("postgres"):
        return url
    return str(ROOT / "redecor.db")


def dump_database(source: str, dest: Path) -> str:
    """Write a consistent copy of the database to dest. Returns 'sqlite' or 'postgres'."""
    if source.startswith("postgres"):
        if not shutil.which("pg_dump"):
            raise RuntimeError("DATABASE_URL is PostgreSQL but pg_dump is not installed")
        dsn = source.replace("postgresql+psycopg://", "postgresql://")
        subprocess.run(["pg_dump", "--no-owner", "--format=plain", f"--file={dest}", dsn], check=True)
        return "postgres"
    src = Path(source)
    if not src.exists():
        raise FileNotFoundError(f"database not found: {src}")
    with sqlite3.connect(f"file:{src}?mode=ro", uri=True) as s, sqlite3.connect(dest) as d:
        s.backup(d)
    return "sqlite"


def verify_zip(path: Path) -> dict:
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad:
            raise RuntimeError(f"corrupt member in zip: {bad}")
        manifest = json.loads(z.read("manifest.json"))
        if manifest["engine"] == "sqlite":
            with tempfile.TemporaryDirectory() as tmp:
                z.extract("redecor.db", tmp)
                db = Path(tmp) / "redecor.db"
                if sha256(db) != manifest["db_sha256"]:
                    raise RuntimeError("database checksum mismatch")
                with sqlite3.connect(db) as con:
                    if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise RuntimeError("database integrity_check failed")
                    con.execute("SELECT count(*) FROM projects").fetchone()
        return manifest


def run_once(a) -> Path:
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = out_dir / f"redecor-backup-{stamp}.zip"
    partial = target.with_suffix(".zip.partial")
    uploads = Path(a.uploads)
    with tempfile.TemporaryDirectory() as tmp:
        db_copy = Path(tmp) / "redecor.db"
        engine = dump_database(a.db, db_copy)
        files = [f for f in uploads.rglob("*") if f.is_file()] if uploads.exists() else []
        att_dir = Path(getattr(a, "attachments", "") or "")
        attachments = [f for f in att_dir.rglob("*") if f.is_file()] if str(att_dir) not in ("", ".") and att_dir.exists() else []
        manifest = {
            "created": stamp,
            "engine": engine,
            "db_sha256": sha256(db_copy),
            "db_bytes": db_copy.stat().st_size,
            "upload_files": len(files),
            "upload_bytes": sum(f.stat().st_size for f in files),
            "attachment_files": len(attachments),
        }
        with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(db_copy, "redecor.db" if engine == "sqlite" else "redecor.sql")
            for f in files:
                z.write(f, Path("uploads") / f.relative_to(uploads))
            for f in attachments:  # private enquiry attachments (separate volume)
                z.write(f, Path("attachments") / f.relative_to(att_dir))
            z.writestr("manifest.json", json.dumps(manifest, indent=2))
    partial.replace(target)
    verify_zip(target)
    log(f"OK {target.name}: database {manifest['db_bytes']} bytes, {manifest['upload_files']} files, "
        f"{manifest['attachment_files']} attachments")

    if a.copy_to:
        dest_dir = Path(a.copy_to)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / target.name
        shutil.copy2(target, dest)
        if sha256(dest) != sha256(target):
            raise RuntimeError(f"off-server copy differs from the original: {dest}")
        log(f"copied and verified: {dest}")
        prune(dest_dir, a.keep)
    prune(out_dir, a.keep)
    return target


def prune(folder: Path, keep: int) -> None:
    backups = sorted(folder.glob("redecor-backup-*.zip"), key=lambda f: f.name, reverse=True)
    for old in backups[keep:]:
        old.unlink()
        log(f"removed old backup {old.name}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=default_db(), help="SQLite file or PostgreSQL URL (default: from DATABASE_URL)")
    ap.add_argument("--uploads", default=os.getenv("UPLOAD_DIR", str(ROOT / "uploads")))
    ap.add_argument("--attachments", default=os.getenv("ATTACHMENTS_DIR", str(ROOT / "attachments")),
                    help="private enquiry attachments folder")
    ap.add_argument("--out-dir", default=os.getenv("BACKUP_DIR", "backups"))
    ap.add_argument("--keep", type=int, default=int(os.getenv("BACKUP_KEEP", "14")), help="how many backups to keep")
    ap.add_argument("--copy-to", default=os.getenv("BACKUP_COPY_TO", ""), help="second location (network share / cloud-synced folder)")
    ap.add_argument("--loop-hours", type=float, default=0, help="keep running and back up every N hours")
    ap.add_argument("--verify", help="only verify an existing backup zip")
    a = ap.parse_args()
    if a.verify:
        m = verify_zip(Path(a.verify))
        log(f"verified {a.verify}: {m}")
        return 0
    while True:
        try:
            run_once(a)
            status = 0
        except Exception as e:  # noqa: BLE001
            log(f"FAILED: {type(e).__name__}: {e}")
            alert(f"FAILED: {type(e).__name__}: {e}")
            status = 1
        if not a.loop_hours:
            return status
        time.sleep(a.loop_hours * 3600)


if __name__ == "__main__":
    sys.exit(main())
