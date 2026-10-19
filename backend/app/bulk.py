"""Bulk project-photo upload: plan (dry-run, writes nothing) and apply.

File naming convention (see docs/CONTENT_GUIDE.md):
    <project-slug>__<nn>__<render|executed>[__cover].<jpg|jpeg|png|webp>
    e.g.  villa-zamalek__01__executed__cover.jpg
An optional CSV mapping (filename,project_slug,order,kind,is_cover,alt_en,alt_ar) overrides the convention
for the files it lists. Used by the admin page and by tools/bulk_images.py.
"""

import csv
import hashlib
import io
import re
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .config import settings
from .db import _sqlite_path, sqlite_backup
from .images import probe, quality_problems
from .models import ImportLog, Project, User

NAME_RE = re.compile(r"^(?P<slug>[a-z0-9][a-z0-9\-]*)__(?P<nn>\d{1,3})__(?P<kind>render|executed)(?P<cover>__cover)?\.(?:jpe?g|png|webp)$", re.I)
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp")
MAX_FILES = 500


@dataclass
class PlanRow:
    file: str
    project_slug: str = ""
    project: str = "NO MATCH"
    order: int | None = None
    kind: str = ""
    cover: bool = False
    alt_en: str = ""
    alt_ar: str = ""
    quality: str = "ok"
    action: str = "reject"  # create | skip-duplicate | reject
    reason: str = ""
    sha256: str = field(default="", repr=False)


def read_mapping(raw: bytes | None) -> dict[str, dict]:
    if not raw:
        return {}
    text = raw.decode("utf-8-sig")
    rows = {}
    for r in csv.DictReader(io.StringIO(text)):
        name = (r.get("filename") or "").strip()
        if name:
            rows[name.lower()] = {k: (v or "").strip() for k, v in r.items() if k}
    return rows


def expand_zip(name: str, raw: bytes) -> list[tuple[str, bytes]]:
    """Image files inside a zip (flat names only; directories, hidden files and non-images are ignored)."""
    out = []
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            infos = [i for i in z.infolist() if not i.is_dir()]
            if len(infos) > MAX_FILES or sum(i.file_size for i in infos) > 2 * 1024**3:
                raise HTTPException(413, f"{name}: too many or too large files in the zip")
            for i in infos:
                base = Path(i.filename.replace("\\", "/")).name
                if base.startswith(".") or not base.lower().endswith(IMAGE_EXT):
                    continue
                out.append((base, z.read(i)))
    except zipfile.BadZipFile:
        raise HTTPException(400, f"{name} is not a valid zip file") from None
    return out


def _truthy(v: str) -> bool:
    return v.strip().lower() in ("1", "true", "yes", "y", "cover")


def plan(db: Session, files: list[tuple[str, bytes]], mapping: dict[str, dict] | None = None, override: bool = False) -> list[PlanRow]:
    """Dry-run: decide what would happen to every file. Never writes to the database or the disk."""
    mapping = mapping or {}
    projects = {p.slug: p for p in db.scalars(select(Project).options(selectinload(Project.images))).unique()}
    seen: dict[str, str] = {}
    rows: list[PlanRow] = []
    for name, raw in files:
        row = PlanRow(file=name, sha256=hashlib.sha256(raw).hexdigest())
        rows.append(row)
        m = mapping.get(name.lower())
        if m:
            row.project_slug = m.get("project_slug", "")
            row.order = int(m["order"]) if (m.get("order") or "").isdigit() else None
            row.kind = (m.get("kind") or "").lower()
            row.cover = _truthy(m.get("is_cover", ""))
            row.alt_en, row.alt_ar = m.get("alt_en", ""), m.get("alt_ar", "")
        else:
            nm = NAME_RE.match(name)
            if not nm:
                row.reason = "name does not follow <slug>__<nn>__<render|executed>[__cover].<ext> and is not in the CSV"
                continue
            row.project_slug, row.order = nm["slug"].lower(), int(nm["nn"])
            row.kind, row.cover = nm["kind"].lower(), bool(nm["cover"])
        if row.kind not in ("render", "executed"):
            row.reason = "kind must be render or executed"
            continue
        p = projects.get(row.project_slug)
        if not p:
            row.reason = f"no project with slug '{row.project_slug}'"
            continue
        row.project = p.title_en
        if row.sha256 in seen:
            row.action, row.reason = "skip-duplicate", f"same file as {seen[row.sha256]}"
            continue
        if any(i.image.sha256 == row.sha256 for i in p.images):
            row.action, row.reason = "skip-duplicate", "already attached to this project"
            continue
        seen[row.sha256] = name
        try:
            w, h = probe(raw)
        except HTTPException as e:
            row.quality, row.reason = "invalid", str(e.detail)
            continue
        problems = quality_problems(w, h, cover=row.cover)
        if problems:
            row.quality = "; ".join(problems)
            if not override:
                row.reason = "below quality standard (tick override to accept)"
                continue
        row.action = "create"
    return rows


def backup_db(reason: str) -> str:
    """Verified copy of the database before a bulk write. SQLite only (PostgreSQL: use tools/backup.py)."""
    src = _sqlite_path()
    if not src or not src.exists():
        return ""
    folder = Path(settings.backup_dir) if settings.backup_dir else src.parent
    dest = sqlite_backup(folder / f"{src.name}.{reason}-{datetime.now():%Y%m%d-%H%M%S}.bak")
    if dest.stat().st_size == 0:
        raise HTTPException(500, "Backup before import is empty: nothing was changed")
    return str(dest)


def apply(db: Session, files: list[tuple[str, bytes]], user: User, mapping: dict[str, dict] | None = None,
          override: bool = False, filename: str = "bulk upload") -> tuple[list[PlanRow], str]:
    """Re-plan (the confirm step shows exactly this table), back up, then create the 'create' rows."""
    from .routers.admin import add_project_image

    rows = plan(db, files, mapping, override)
    todo = [r for r in rows if r.action == "create"]
    backup = backup_db("pre-bulk-images") if todo else ""
    by_name = dict(files)
    projects = {p.slug: p for p in db.scalars(select(Project).options(selectinload(Project.images))).unique()}
    for r in todo:
        p = projects[r.project_slug]
        add_project_image(db, p, by_name[r.file], user, kind=r.kind, order=r.order, cover=r.cover or None,
                          alt_en=r.alt_en, alt_ar=r.alt_ar, override=override)
    db.add(ImportLog(user_email=user.email, kind="images", filename=filename[:255], created=len(todo),
                     skipped=sum(r.action == "skip-duplicate" for r in rows), errors=sum(r.action == "reject" for r in rows),
                     backup_file=backup))
    db.commit()
    return rows, backup


def rows_json(rows: list[PlanRow]) -> list[dict]:
    return [{k: v for k, v in asdict(r).items() if k != "sha256"} for r in rows]
