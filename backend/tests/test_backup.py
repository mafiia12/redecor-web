"""tools/backup.py + tools/restore.py round trip on the test database."""

import sqlite3
import subprocess
import sys
import zipfile
from pathlib import Path

from app.config import settings

TOOLS = Path(__file__).resolve().parents[2] / "tools"


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)


def test_backup_verify_retention_offsite_and_restore(client, auth, tmp_path):
    client.post("/api/admin/projects", headers=auth, json={"title_en": "Backup Me", "country": "eg", "type": "office"})
    db = settings.database_url.split("sqlite:///", 1)[1]
    out, copy = tmp_path / "out", tmp_path / "nas"
    for _ in range(3):
        r = run(TOOLS / "backup.py", "--db", db, "--uploads", settings.upload_dir, "--out-dir", out, "--keep", "2", "--copy-to", copy)
        assert r.returncode == 0, r.stdout + r.stderr
        import time

        time.sleep(1.1)  # distinct timestamps
    zips = sorted(out.glob("redecor-backup-*.zip"))
    assert len(zips) == 2 and len(list(copy.glob("*.zip"))) == 2  # retention on both sides
    assert run(TOOLS / "backup.py", "--verify", zips[-1]).returncode == 0

    # a corrupted backup is detected
    bad = tmp_path / "bad.zip"
    data = bytearray(zips[-1].read_bytes())
    data[200:260] = b"x" * 60
    bad.write_bytes(bytes(data))
    assert run(TOOLS / "backup.py", "--verify", bad).returncode != 0

    # restore into a fresh place, previous files are moved aside (never deleted)
    target_db, target_up = tmp_path / "restore" / "redecor.db", tmp_path / "restore" / "uploads"
    target_db.parent.mkdir()
    target_db.write_text("old")
    r = run(TOOLS / "restore.py", zips[-1], "--db", target_db, "--uploads", target_up)
    assert r.returncode == 0, r.stdout + r.stderr
    titles = [t for (t,) in sqlite3.connect(target_db).execute("SELECT title_en FROM projects")]
    assert "Backup Me" in titles
    assert list(target_db.parent.glob("redecor.db.before-restore-*"))
    with zipfile.ZipFile(zips[-1]) as z:
        assert "manifest.json" in z.namelist()


def test_backup_fails_loudly_without_database(tmp_path):
    r = run(TOOLS / "backup.py", "--db", tmp_path / "missing.db", "--uploads", tmp_path, "--out-dir", tmp_path / "o")
    assert r.returncode == 1 and "FAILED" in r.stdout
