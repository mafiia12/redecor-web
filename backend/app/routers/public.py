import hashlib
import json
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import AnalyticsDaily, Client, Enquiry, Office, Project, SiteDocument, SiteImage, Testimonial
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


@router.post("/enquiries", status_code=201)
def create_enquiry(data: EnquiryIn, request: Request, background: BackgroundTasks, db: Session = Depends(get_db)):
    # Bots: honeypot filled, or the form was submitted faster than a person can type. Pretend success, store nothing.
    if data.website or (data.elapsed_ms is not None and data.elapsed_ms < MIN_FILL_MS):
        return {"ok": True}
    enquiry_limiter.check(client_ip(request))
    fp = _fingerprint(data)
    since = datetime.now(timezone.utc) - DUPLICATE_WINDOW
    dup = db.scalar(select(Enquiry).where(Enquiry.fingerprint == fp, Enquiry.created_at >= since))
    if dup:  # double click / resend: keep one row and one notification
        return {"ok": True, "duplicate": True}
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
    db.commit()  # stored first: a notification problem can never lose the enquiry
    background.add_task(deliver, e.id)
    return {"ok": True}


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
