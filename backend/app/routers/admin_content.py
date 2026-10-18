"""Admin content tooling: bulk photo upload, approvals register, readiness dashboard, project import."""

import json
import secrets
import shutil
import time
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import attachments, bulk, importer, private_files, sheets
from ..config import settings
from ..db import get_db
from ..models import Approval, Client, Project, User
from ..security import editor, viewer
from ..visibility import APPROVAL_STATUSES, APPROVAL_TYPES, REQUIRED_APPROVAL
from .admin import audit

router = APIRouter(prefix="/api/admin", tags=["admin"])

STAGING_TTL = 2 * 3600


def staging_root() -> Path:
    return settings.attachments_dir / "_staging"  # private: never served


def _clean_staging() -> None:
    root = staging_root()
    if not root.exists():
        return
    for d in root.iterdir():
        if d.is_dir() and time.time() - d.stat().st_mtime > STAGING_TTL:
            shutil.rmtree(d, ignore_errors=True)


def _stage_dir(token: str) -> Path:
    if not token.isalnum() or len(token) != 32:
        raise HTTPException(400, "Invalid upload token")
    d = staging_root() / token
    if not d.is_dir():
        raise HTTPException(404, "This upload expired. Upload the files again.")
    return d


def _staged(token: str) -> tuple[list[tuple[str, bytes]], dict, Path]:
    d = _stage_dir(token)
    meta = json.loads((d / "meta.json").read_text())
    files = [(name, (d / f"{i}.bin").read_bytes()) for i, name in enumerate(meta["names"])]
    mapping = bulk.read_mapping((d / "mapping.csv").read_bytes()) if (d / "mapping.csv").exists() else {}
    return files, mapping, d


# ---------- bulk images ----------
@router.post("/bulk-images/plan")
def bulk_plan(
    files: list[UploadFile] = File(...),
    mapping: UploadFile | None = File(None),
    override_quality: bool = Form(False),
    db: Session = Depends(get_db),
    _: User = Depends(editor),
):
    """Dry-run. Files (or zips of files) are kept in a private staging folder for the confirm step;
    nothing is written to the database or the public uploads."""
    _clean_staging()
    items: list[tuple[str, bytes]] = []
    for f in files:
        raw = f.file.read(200 * 1024 * 1024 + 1)
        name = Path(f.filename or "file").name
        if name.lower().endswith(".zip"):
            items += bulk.expand_zip(name, raw)
        else:
            items.append((name, raw))
    if not items:
        raise HTTPException(400, "No image files found")
    if len(items) > bulk.MAX_FILES:
        raise HTTPException(413, f"At most {bulk.MAX_FILES} files per batch")
    map_raw = mapping.file.read(2 * 1024 * 1024) if mapping else None
    token = secrets.token_hex(16)
    d = staging_root() / token
    d.mkdir(parents=True)
    for i, (_, raw) in enumerate(items):
        (d / f"{i}.bin").write_bytes(raw)
    (d / "meta.json").write_text(json.dumps({"names": [n for n, _ in items]}))
    if map_raw:
        (d / "mapping.csv").write_bytes(map_raw)
    rows = bulk.plan(db, items, bulk.read_mapping(map_raw), override_quality)
    return {"token": token, "rows": bulk.rows_json(rows), "summary": _summary(rows)}


def _summary(rows) -> dict:
    out = {"create": 0, "skip-duplicate": 0, "reject": 0}
    for r in rows:
        out[r.action] += 1
    return out


@router.post("/bulk-images/apply")
def bulk_apply(token: str = Form(...), override_quality: bool = Form(False), db: Session = Depends(get_db),
               user: User = Depends(editor)):
    files, mapping, d = _staged(token)
    rows, backup = bulk.apply(db, files, user, mapping, override_quality, filename=f"admin bulk upload ({len(files)} files)")
    shutil.rmtree(d, ignore_errors=True)
    return {"rows": bulk.rows_json(rows), "summary": _summary(rows), "backup": Path(backup).name if backup else ""}


@router.get("/bulk-images/mapping-template")
def mapping_template(_: User = Depends(editor)):
    body = "filename,project_slug,order,kind,is_cover,alt_en,alt_ar\n"
    return Response(body.encode("utf-8-sig"), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="image-mapping-template.csv"'})


# ---------- approvals register (append-only) ----------
def _approval_out(a: Approval) -> dict:
    return {
        "id": a.id, "subject_type": a.subject_type, "subject_id": a.subject_id, "approval_type": a.approval_type,
        "status": a.status, "approved_by_name": a.approved_by_name, "approver_organization": a.approver_organization,
        "approval_date": a.approval_date.isoformat() if a.approval_date else None, "evidence_note": a.evidence_note,
        "has_evidence": bool(a.evidence_file), "evidence_filename": a.evidence_filename or "",
        "recorded_by": a.recorded_by, "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def current_status(db: Session, subject_type: str, subject_id: int, approval_type: str | None = None) -> str:
    a_type = approval_type or REQUIRED_APPROVAL[subject_type]
    row = db.scalar(select(Approval).where(Approval.subject_type == subject_type, Approval.subject_id == subject_id,
                                           Approval.approval_type == a_type).order_by(Approval.id.desc()).limit(1))
    return row.status if row else "none"


def _subject_exists(db: Session, subject_type: str, subject_id: int) -> bool:
    model = {"project": Project, "client": Client}.get(subject_type)
    return bool(model and db.get(model, subject_id))


@router.get("/approvals")
def list_approvals(subject_type: str, subject_id: int, db: Session = Depends(get_db), _: User = Depends(viewer)):
    rows = db.scalars(select(Approval).where(Approval.subject_type == subject_type, Approval.subject_id == subject_id)
                      .order_by(Approval.id.desc())).all()
    required = REQUIRED_APPROVAL.get(subject_type)
    return {"required_type": required, "current": current_status(db, subject_type, subject_id) if required else "none",
            "history": [_approval_out(a) for a in rows]}


@router.post("/approvals", status_code=201)
def record_approval(
    subject_type: str = Form(...),
    subject_id: int = Form(...),
    approval_type: str = Form(...),
    status: str = Form(...),
    approved_by_name: str = Form(""),
    approver_organization: str = Form(""),
    approval_date: str = Form(""),
    evidence_note: str = Form(""),
    evidence: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(editor),
):
    """Adds a NEW row. Existing rows are never edited or deleted (there is no PUT or DELETE)."""
    if subject_type not in REQUIRED_APPROVAL or not _subject_exists(db, subject_type, subject_id):
        raise HTTPException(404, "Unknown project or client")
    if approval_type not in APPROVAL_TYPES:
        raise HTTPException(422, f"approval_type must be one of {', '.join(APPROVAL_TYPES)}")
    if status not in APPROVAL_STATUSES:
        raise HTTPException(422, f"status must be one of {', '.join(APPROVAL_STATUSES)}")
    if status == "approved" and not (approved_by_name.strip() and evidence_note.strip()):
        raise HTTPException(422, "An approval needs who gave it and how (e-mail, letter, verbal…)")
    try:
        day = date.fromisoformat(approval_date) if approval_date else None
    except ValueError:
        raise HTTPException(422, "approval_date must be YYYY-MM-DD") from None
    a = Approval(subject_type=subject_type, subject_id=subject_id, approval_type=approval_type, status=status,
                 approved_by_name=approved_by_name.strip()[:160], approver_organization=approver_organization.strip()[:160],
                 approval_date=day, evidence_note=evidence_note.strip()[:500], recorded_by=user.email)
    if evidence is not None and evidence.filename:
        raw = evidence.file.read(settings.attach_max_file_mb * 1024 * 1024 + 1)
        kind, problem = attachments.inspect(raw, evidence.filename)
        if problem:
            raise HTTPException(415, f"Evidence file rejected: {problem}")
        a.evidence_file = private_files.save("evidence", raw)
        a.evidence_filename = f"{private_files.clean_name(evidence.filename)}|{kind}"
    db.add(a)
    db.flush()
    audit(db, user, f"approval:{status}", subject_type, subject_id)
    db.commit()
    return _approval_out(a)


@router.get("/approvals/{aid}/evidence")
def approval_evidence(aid: int, db: Session = Depends(get_db), user: User = Depends(editor)):
    a = db.get(Approval, aid)
    if not a or not a.evidence_file:
        raise HTTPException(404, "No evidence file")
    name, _, kind = (a.evidence_filename or "evidence|bin").rpartition("|")
    audit(db, user, "download", "approval_evidence", aid)
    db.commit()
    return private_files.download("evidence", a.evidence_file, name, kind)


def gate_report(db: Session) -> dict:
    """Published items that the approvals gate hides because no current approval is on record."""
    projects = db.scalars(select(Project).where(Project.published.is_(True)).order_by(Project.sort_order, Project.id)).all()
    clients = db.scalars(select(Client).where(Client.published.is_(True)).order_by(Client.sort_order, Client.id)).all()
    hidden_p = [{"id": p.id, "slug": p.slug, "title": p.title_en, "status": current_status(db, "project", p.id)}
                for p in projects if current_status(db, "project", p.id) != "approved"]
    hidden_c = [{"id": c.id, "name": c.name, "status": current_status(db, "client", c.id)}
                for c in clients if current_status(db, "client", c.id) != "approved"]
    return {"enforced": settings.enforce_approvals, "projects_hidden": hidden_p, "clients_hidden": hidden_c,
            "counts": {"projects": len(hidden_p), "clients": len(hidden_c)}}


@router.get("/approvals/gate-report")
def approvals_gate_report(db: Session = Depends(get_db), _: User = Depends(viewer)):
    return gate_report(db)


# ---------- content readiness ----------
def readiness_rows(db: Session) -> list[dict]:
    rows = []
    for p in db.scalars(select(Project).options(selectinload(Project.images)).order_by(Project.sort_order, Project.id)).unique():
        imgs = p.images
        cover = next((i for i in imgs if i.is_cover), imgs[0] if imgs else None)
        checks = {
            "title_en": bool(p.title_en.strip()),
            "title_ar": bool(p.title_ar.strip()),
            "description_en": bool(p.summary_en.strip()),
            "description_ar": bool(p.summary_ar.strip()),
            "cover_image": cover is not None,
            "every_image_has_kind": bool(imgs) and all(i.kind in ("render", "executed") for i in imgs),
            "alt_text_en_ar": bool(imgs) and all((i.alt_en or "").strip() and (i.alt_ar or "").strip() for i in imgs),
            "approved": current_status(db, "project", p.id) == "approved",
        }
        missing = [k for k, ok in checks.items() if not ok]
        rows.append({"type": "project", "id": p.id, "slug": p.slug, "name": p.title_en, "name_ar": p.title_ar,
                     "image_count": len(imgs),
                     **checks, "approval_status": current_status(db, "project", p.id), "published": p.published,
                     "missing": len(missing), "missing_items": ", ".join(missing), "ready": not missing})
    for c in db.scalars(select(Client).order_by(Client.sort_order, Client.id)):
        checks = {"logo": c.logo_image_id is not None, "approved": current_status(db, "client", c.id) == "approved"}
        missing = [k for k, ok in checks.items() if not ok]
        rows.append({"type": "client", "id": c.id, "slug": "", "name": c.name, "name_ar": "", "image_count": 1 if c.logo_image_id else 0,
                     **checks, "approval_status": current_status(db, "client", c.id), "published": c.published,
                     "missing": len(missing), "missing_items": ", ".join(missing), "ready": not missing})
    return rows


READINESS_COLUMNS = ["type", "name", "name_ar", "slug", "title_en", "title_ar", "description_en", "description_ar", "cover_image",
                     "image_count", "every_image_has_kind", "alt_text_en_ar", "logo", "approval_status", "published",
                     "missing", "missing_items", "ready"]


@router.get("/readiness")
def readiness(format: str = "json", db: Session = Depends(get_db), _: User = Depends(viewer)):
    rows = readiness_rows(db)
    if format in ("csv", "xlsx"):
        return sheets.export(rows, READINESS_COLUMNS, "content-readiness", format)
    projects = [r for r in rows if r["type"] == "project"]
    clients = [r for r in rows if r["type"] == "client"]
    return {"rows": rows, "summary": {"projects_ready": sum(r["ready"] for r in projects), "projects": len(projects),
                                      "clients_ready": sum(r["ready"] for r in clients), "clients": len(clients)}}


# ---------- project import (Excel / CSV / JSON manifest) ----------
IMPORT_MAX = 20 * 1024 * 1024


def _import_rows(file: UploadFile) -> tuple[list, bytes]:
    raw = file.file.read(IMPORT_MAX + 1)
    if len(raw) > IMPORT_MAX:
        raise HTTPException(413, "Import file is larger than 20 MB")
    return importer.read(file.filename or "", raw), raw


@router.get("/import/template")
def import_template(_: User = Depends(editor)):
    return Response(importer.template_xlsx(),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="project-import-template.xlsx"'})


@router.post("/import/plan")
def import_plan(file: UploadFile = File(...), update_existing: bool = Form(False), db: Session = Depends(get_db),
                _: User = Depends(editor)):
    """Dry-run: nothing is written."""
    rows, _raw = _import_rows(file)
    planned = importer.plan(db, rows, update_existing)
    return {"rows": importer.rows_json(planned), "summary": importer.summary(planned)}


@router.post("/import/apply")
def import_apply(file: UploadFile = File(...), update_existing: bool = Form(False), db: Session = Depends(get_db),
                 user: User = Depends(editor)):
    rows, _raw = _import_rows(file)
    planned, backup = importer.apply(db, rows, user, update_existing, filename=file.filename or "import")
    return {"rows": importer.rows_json(planned), "summary": importer.summary(planned),
            "backup": Path(backup).name if backup else ""}


@router.get("/import/log")
def import_log(db: Session = Depends(get_db), _: User = Depends(viewer)):
    from ..models import ImportLog

    rows = db.scalars(select(ImportLog).order_by(ImportLog.id.desc()).limit(50))
    return [{"at": r.at.isoformat(), "user": r.user_email, "kind": r.kind, "filename": r.filename, "created": r.created,
             "updated": r.updated, "skipped": r.skipped, "errors": r.errors, "backup": Path(r.backup_file).name if r.backup_file else ""}
            for r in rows]
