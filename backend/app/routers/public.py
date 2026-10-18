import hashlib
import json
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, Response, UploadFile
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import attachments, private_files
from ..alerts import alert
from ..config import settings
from ..db import SessionLocal, get_db
from ..models import AnalyticsDaily, Client, Enquiry, EnquiryAttachment, Office, Project, SiteDocument, SiteImage, Testimonial
from ..notify import deliver
from ..schemas import (
    BootstrapOut,
    DocumentOut,
    EnquiryIn,
    EventIn,
    OfficeOut,
    ProjectDetailOut,
    SiteImageOut,
    TestimonialOut,
    image_out,
)
from ..security import RateLimiter, client_ip
from ..serializers import card_out, client_out, detail_out
from ..visibility import clean_office, public_clients, public_documents, public_projects, public_testimonials

router = APIRouter(prefix="/api", tags=["public"])
enquiry_limiter = RateLimiter(limit=5, window_s=600)
event_limiter = RateLimiter(limit=240, window_s=600)

MIN_FILL_MS = 2500  # a person needs longer than this to fill the form
DUPLICATE_WINDOW = timedelta(minutes=30)


def published_projects(db: Session) -> list[Project]:
    return list(
        db.scalars(
            select(Project)
            .where(public_projects())
            .options(selectinload(Project.images))
            .order_by(Project.sort_order, Project.id)
        ).unique()
    )


def _etag_json(request: Request, payload: dict) -> Response:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    etag = '"' + hashlib.md5(body, usedforsecurity=False).hexdigest() + '"'  # cache validator only
    headers = {"ETag": etag, "Cache-Control": "no-cache"}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return Response(body, media_type="application/json", headers=headers)


@router.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"ok": True}


def document_out(d: SiteDocument) -> DocumentOut:
    return DocumentOut(slot=d.slot, url=f"/media/docs/{d.key}.pdf", filename=d.filename, size=d.size)


@router.get("/bootstrap")
def bootstrap(request: Request, db: Session = Depends(get_db)):
    """One request gives the public site everything it needs for first paint."""
    offices = [OfficeOut(**clean_office(o)) for o in db.scalars(select(Office).order_by(Office.country))]
    site_images = {
        s.slot: SiteImageOut(slot=s.slot, alt_en=s.alt_en, alt_ar=s.alt_ar, image=image_out(s.image))
        for s in db.scalars(select(SiteImage))
    }
    clients = [client_out(c) for c in db.scalars(select(Client).where(public_clients()).order_by(Client.sort_order, Client.id))]
    testimonials = [
        TestimonialOut.model_validate(t, from_attributes=True)
        for t in db.scalars(select(Testimonial).where(public_testimonials()).order_by(Testimonial.sort_order, Testimonial.id))
    ]
    documents = {d.slot: document_out(d) for d in db.scalars(select(SiteDocument).where(public_documents()))}
    data = BootstrapOut(
        offices=offices,
        site_images=site_images,
        clients=clients,
        projects=[card_out(p) for p in published_projects(db)],
        testimonials=testimonials,
        documents=documents,
        attachments={"max_files": settings.attach_max_files, "max_file_mb": settings.attach_max_file_mb,
                     "max_total_mb": settings.attach_max_total_mb},
    )
    return _etag_json(request, data.model_dump(mode="json"))


def find_public_project(db: Session, slug: str) -> Project | None:
    return db.scalar(select(Project).where(Project.slug == slug, public_projects()).options(selectinload(Project.images)))


def project_payload(db: Session, p: Project) -> ProjectDetailOut:
    ordered = published_projects(db)
    others = [x for x in ordered if x.id != p.id]
    similar = [x for x in others if x.country == p.country or x.type == p.type]
    related = (similar + [x for x in others if x not in similar])[:3]
    idx = next((i for i, x in enumerate(ordered) if x.id == p.id), None)
    prev = nxt = None
    if idx is not None and len(ordered) > 1:
        prev = ordered[idx - 1] if idx > 0 else None
        nxt = ordered[idx + 1] if idx + 1 < len(ordered) else None
    return detail_out(p, related, prev, nxt)


@router.get("/projects/{slug}", response_model=ProjectDetailOut)
def project_detail(slug: str, db: Session = Depends(get_db)):
    p = find_public_project(db, slug)
    if not p:
        raise HTTPException(404, "Project not found")
    return project_payload(db, p)


def _fingerprint(data: EnquiryIn) -> str:
    phone = re.sub(r"\D", "", data.phone)
    raw = "|".join([data.name.lower(), phone, data.email.lower(), data.service, data.message[:500].lower()])
    return hashlib.sha256(raw.encode()).hexdigest()


def _store_enquiry(data: EnquiryIn, request: Request, db: Session, files: list | None = None) -> tuple[Enquiry | None, dict]:
    """Shared by the plain and the with-files form. Returns (enquiry or None when nothing is stored, response).
    Files are checked BEFORE anything is stored, so a rejected file never leaves a half-saved enquiry."""
    # Bots: honeypot filled, or the form was submitted faster than a person can type. Pretend success, store nothing.
    if data.website or (data.elapsed_ms is not None and data.elapsed_ms < MIN_FILL_MS):
        return None, {"ok": True}
    enquiry_limiter.check(client_ip(request))
    checked = check_files(files) if files else []
    fp = _fingerprint(data)
    since = datetime.now(timezone.utc) - DUPLICATE_WINDOW
    dup = db.scalar(select(Enquiry).where(Enquiry.fingerprint == fp, Enquiry.created_at >= since))
    if dup:  # double click / resend: keep one row and one notification
        return None, {"ok": True, "duplicate": True}
    message = data.message
    if data.source:
        message = f"{message}\n\n[Sent from: {data.source}]".strip()
    e = Enquiry(
        name=data.name,
        phone=data.phone,
        email=data.email,
        country=data.country,
        service=data.service,
        project_type=data.project_type,
        area_m2=data.area_m2,
        message=message,
        contact_method=data.contact_method,
        lang=data.lang,
        fingerprint=fp,
        notify_status="pending",
        source_page=data.source[:200] or None,
    )
    db.add(e)
    db.flush()
    for name, raw, kind in checked:
        stored = private_files.save("attachments", raw)
        db.add(EnquiryAttachment(enquiry_id=e.id, stored_name=stored, original_name=private_files.clean_name(name),
                                 size=len(raw), detected_type=kind, sha256=hashlib.sha256(raw).hexdigest(),
                                 scan_status="quarantine", scan_detail="waiting for scan"))
    db.commit()  # stored first: a notification or scan problem can never lose the enquiry
    return e, {"ok": True}


@router.post("/enquiries", status_code=201)
def create_enquiry(data: EnquiryIn, request: Request, background: BackgroundTasks, db: Session = Depends(get_db)):
    e, out = _store_enquiry(data, request, db)
    if e:
        background.add_task(deliver, e.id)
    return out


def check_files(files: list) -> list[tuple[str, bytes, str]]:
    """Limits and content checks for quote attachments. Errors carry a code the form translates (EN/AR)."""
    max_file = settings.attach_max_file_mb * 1024 * 1024
    max_total = settings.attach_max_total_mb * 1024 * 1024
    if len(files) > settings.attach_max_files:
        raise HTTPException(422, {"code": "too_many_files", "max": settings.attach_max_files})
    out, total = [], 0
    for f in files:
        name = private_files.clean_name(f.filename or "file")
        raw = f.file.read(max_file + 1)  # UploadFile is spooled to disk while streaming; read at most the limit
        if len(raw) > max_file:
            raise HTTPException(413, {"code": "file_too_large", "file": name, "max_mb": settings.attach_max_file_mb})
        total += len(raw)
        if total > max_total:
            raise HTTPException(413, {"code": "total_too_large", "max_mb": settings.attach_max_total_mb})
        kind, problem = attachments.inspect(raw, name)
        if not kind:
            raise HTTPException(422, {"code": "file_type", "file": name, "reason": problem})
        out.append((name, raw, kind))
    return out


def scan_then_notify(enquiry_id: int) -> None:
    """Virus scan (when enabled) after the enquiry is safely stored; a scanner failure only marks the files."""
    with SessionLocal() as db:
        for a in db.scalars(select(EnquiryAttachment).where(EnquiryAttachment.enquiry_id == enquiry_id)):
            try:
                status, detail = attachments.scan(private_files.path_of("attachments", a.stored_name).read_bytes())
            except Exception as exc:  # noqa: BLE001 - never lose the enquiry over a scan
                status, detail = "error", f"scan failed ({type(exc).__name__})"
            a.scan_status, a.scan_detail = status, detail[:200]
            if status == "infected":
                alert("attachment-infected", f"Enquiry #{enquiry_id}: file {a.id} flagged by the virus scanner ({detail[:80]})")
        db.commit()
    deliver(enquiry_id)


@router.post("/enquiries/with-files", status_code=201)
def create_enquiry_with_files(
    request: Request, background: BackgroundTasks, data: str = Form(...), files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    """Quote form with up to ATTACH_MAX_FILES files. `data` is the same JSON as POST /api/enquiries."""
    try:
        parsed = EnquiryIn.model_validate_json(data)
    except ValidationError as exc:
        raise HTTPException(422, [{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()]) from None
    e, out = _store_enquiry(parsed, request, db, [f for f in files if f.filename])
    if e:
        background.add_task(scan_then_notify, e.id)
    return out


_PATH_RE = re.compile(r"^/[A-Za-z0-9\-_/]*$")


@router.post("/events", status_code=204)
def track_event(data: EventIn, request: Request, db: Session = Depends(get_db)):
    """Anonymous, cookie-free counters. The IP is used only in memory for rate limiting and never stored."""
    try:
        event_limiter.check(client_ip(request))
    except HTTPException:
        return Response(status_code=204)
    path = data.path.split("?", 1)[0].split("#", 1)[0][:200]
    if not _PATH_RE.match(path):
        path = ""
    day = datetime.now(timezone.utc).date()
    row = db.scalar(
        select(AnalyticsDaily).where(
            AnalyticsDaily.day == day, AnalyticsDaily.name == data.name, AnalyticsDaily.path == path, AnalyticsDaily.lang == data.lang
        )
    )
    if row:
        row.count += 1
    else:
        db.add(AnalyticsDaily(day=day, name=data.name, path=path, lang=data.lang, count=1))
    try:
        db.commit()
    except Exception:  # noqa: BLE001  (two first hits of the same counter at once: drop one, never fail the page)
        db.rollback()
    return Response(status_code=204)
