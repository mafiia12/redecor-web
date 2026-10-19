"""Admin: users and roles, system status, analytics summary, testimonials and downloadable documents."""

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import AnalyticsDaily, Enquiry, SiteDocument, Testimonial, User
from ..notify import send
from ..schemas import TestimonialAdminOut, TestimonialIn, UserCreateIn, UserOut, UserUpdateIn
from ..security import admin_only, editor, hash_password, password_problems, viewer
from .admin import audit

router = APIRouter(prefix="/api/admin", tags=["admin"])

DOCUMENT_SLOTS = {"company-profile": "Company profile (PDF)"}


# ---------- users & roles (admin only) ----------
@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return db.scalars(select(User).order_by(User.id)).all()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(data: UserCreateIn, db: Session = Depends(get_db), user: User = Depends(admin_only)):
    if db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(409, "A user with this e-mail already exists")
    problems = password_problems(data.password, data.email)
    if problems:
        raise HTTPException(422, " ".join(problems))
    u = User(email=data.email, role=data.role, password_hash=hash_password(data.password))
    db.add(u)
    db.flush()
    audit(db, user, f"create:{data.role}", "user", u.id)
    db.commit()
    return u


def _admins_left(db: Session, excluding: int) -> int:
    return db.scalar(select(func.count()).select_from(User).where(User.role == "admin", User.id != excluding)) or 0


@router.patch("/users/{uid}", response_model=UserOut)
def update_user(uid: int, data: UserUpdateIn, db: Session = Depends(get_db), user: User = Depends(admin_only)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "User not found")
    if data.role and data.role != u.role:
        if u.role == "admin" and _admins_left(db, u.id) == 0:
            raise HTTPException(409, "At least one admin must remain")
        u.role = data.role
        u.token_version = (u.token_version or 0) + 1  # new rights apply from the next sign-in
    if data.password:
        problems = password_problems(data.password, u.email)
        if problems:
            raise HTTPException(422, " ".join(problems))
        u.password_hash = hash_password(data.password)
        u.token_version = (u.token_version or 0) + 1
    audit(db, user, "update", "user", uid)
    db.commit()
    return u


@router.delete("/users/{uid}", status_code=204)
def delete_user(uid: int, db: Session = Depends(get_db), user: User = Depends(admin_only)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "User not found")
    if u.id == user.id:
        raise HTTPException(409, "You cannot delete your own account")
    if u.role == "admin" and _admins_left(db, u.id) == 0:
        raise HTTPException(409, "At least one admin must remain")
    db.delete(u)
    audit(db, user, "delete", "user", uid)
    db.commit()


# ---------- system status ----------
@router.get("/system")
def system_status(db: Session = Depends(get_db), _: User = Depends(viewer)):
    counts = dict(db.execute(select(Enquiry.notify_status, func.count()).group_by(Enquiry.notify_status)).all())
    return {
        "environment": settings.app_env,
        "smtp_configured": settings.smtp_configured,
        "notify_to": settings.notify_to,
        "notifications": counts,
        "alerts_configured": bool(settings.alert_webhook_url),
        "test_content_visible": settings.allow_test_content,
        "demo_seed": settings.seed_demo,
    }


@router.post("/system/test-email")
def test_email(_: User = Depends(admin_only)):
    """Send one test message to NOTIFY_TO to confirm the SMTP settings work."""
    from email.message import EmailMessage

    if not settings.smtp_configured:
        raise HTTPException(409, "SMTP is not configured (SMTP_HOST, MAIL_FROM and NOTIFY_TO are required)")
    msg = EmailMessage()
    msg["Subject"] = "Redecor website: test notification"
    msg["From"], msg["To"] = settings.mail_from, ", ".join(settings.notify_to)
    msg.set_content("This is a test from the Redecor website admin. If you received it, enquiry notifications work.")
    try:
        send(msg)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"SMTP error: {type(e).__name__}") from None
    return {"ok": True, "sent_to": settings.notify_to}


# ---------- analytics ----------
@router.get("/analytics")
def analytics(days: int = 30, db: Session = Depends(get_db), _: User = Depends(viewer)):
    days = max(1, min(days, 366))
    since = date.today() - timedelta(days=days - 1)
    rows = db.execute(
        select(AnalyticsDaily.name, func.sum(AnalyticsDaily.count))
        .where(AnalyticsDaily.day >= since)
        .group_by(AnalyticsDaily.name)
    ).all()
    top = db.execute(
        select(AnalyticsDaily.path, func.sum(AnalyticsDaily.count).label("n"))
        .where(AnalyticsDaily.day >= since, AnalyticsDaily.name == "project_view")
        .group_by(AnalyticsDaily.path)
        .order_by(func.sum(AnalyticsDaily.count).desc())
        .limit(10)
    ).all()
    langs = db.execute(
        select(AnalyticsDaily.lang, func.sum(AnalyticsDaily.count))
        .where(AnalyticsDaily.day >= since, AnalyticsDaily.name == "page_view")
        .group_by(AnalyticsDaily.lang)
    ).all()
    return {
        "days": days,
        "totals": {name: int(n) for name, n in rows},
        "top_projects": [{"path": p, "views": int(n)} for p, n in top],
        "languages": {lang or "-": int(n) for lang, n in langs},
    }


# ---------- testimonials (public only when approved AND published) ----------
@router.get("/testimonials", response_model=list[TestimonialAdminOut])
def list_testimonials(db: Session = Depends(get_db), _: User = Depends(viewer)):
    return db.scalars(select(Testimonial).order_by(Testimonial.sort_order, Testimonial.id)).all()


def _check_testimonial(data: TestimonialIn) -> None:
    if data.published and not data.approved:
        raise HTTPException(422, "Record the client's approval before publishing a testimonial")
    if data.published and not (data.quote_en or data.quote_ar):
        raise HTTPException(422, "A published testimonial needs a quote")


@router.post("/testimonials", response_model=TestimonialAdminOut, status_code=201)
def create_testimonial(data: TestimonialIn, db: Session = Depends(get_db), user: User = Depends(editor)):
    _check_testimonial(data)
    t = Testimonial(**data.model_dump())
    db.add(t)
    db.flush()
    audit(db, user, "create", "testimonial", t.id)
    db.commit()
    return t


@router.put("/testimonials/{tid}", response_model=TestimonialAdminOut)
def update_testimonial(tid: int, data: TestimonialIn, db: Session = Depends(get_db), user: User = Depends(editor)):
    t = db.get(Testimonial, tid)
    if not t:
        raise HTTPException(404, "Testimonial not found")
    _check_testimonial(data)
    for k, v in data.model_dump().items():
        setattr(t, k, v)
    audit(db, user, "update", "testimonial", tid)
    db.commit()
    return t


@router.delete("/testimonials/{tid}", status_code=204)
def delete_testimonial(tid: int, db: Session = Depends(get_db), user: User = Depends(editor)):
    t = db.get(Testimonial, tid)
    if not t:
        raise HTTPException(404, "Testimonial not found")
    db.delete(t)
    audit(db, user, "delete", "testimonial", tid)
    db.commit()


# ---------- downloadable documents (company profile PDF) ----------
def _doc_out(slot: str, d: SiteDocument | None) -> dict:
    return {
        "slot": slot,
        "label": DOCUMENT_SLOTS[slot],
        "filename": d.filename if d else "",
        "size": d.size if d else 0,
        "published": d.published if d else False,
        "url": f"/media/docs/{d.key}.pdf" if d else "",
    }


@router.get("/documents")
def list_documents(db: Session = Depends(get_db), _: User = Depends(viewer)):
    return [_doc_out(slot, db.get(SiteDocument, slot)) for slot in DOCUMENT_SLOTS]


@router.put("/documents/{slot}")
def upload_document(slot: str, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(editor)):
    if slot not in DOCUMENT_SLOTS:
        raise HTTPException(404, "Unknown document")
    raw = file.file.read(settings.max_document_bytes + 1)
    if len(raw) > settings.max_document_bytes:
        raise HTTPException(413, "The PDF is larger than 25 MB.")
    if not raw.startswith(b"%PDF-"):
        raise HTTPException(415, "Upload a PDF file.")
    key = uuid.uuid4().hex
    folder = settings.upload_dir / "docs"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{key}.pdf").write_bytes(raw)
    name = (file.filename or "company-profile.pdf").replace("/", "_").replace("\\", "_")[:150]
    d = db.get(SiteDocument, slot)
    old = d.key if d else None
    if d:
        d.key, d.filename, d.size, d.published = key, name, len(raw), False  # a new file starts unpublished
    else:
        d = SiteDocument(slot=slot, key=key, filename=name, size=len(raw), published=False)
        db.add(d)
    audit(db, user, "upload", "document", slot)
    db.commit()
    if old:
        (folder / f"{old}.pdf").unlink(missing_ok=True)
    return _doc_out(slot, d)


@router.patch("/documents/{slot}")
def publish_document(slot: str, published: bool, db: Session = Depends(get_db), user: User = Depends(editor)):
    d = db.get(SiteDocument, slot)
    if not d:
        raise HTTPException(404, "Upload the file first")
    d.published = published
    audit(db, user, "publish" if published else "unpublish", "document", slot)
    db.commit()
    return _doc_out(slot, d)


@router.delete("/documents/{slot}", status_code=204)
def delete_document(slot: str, db: Session = Depends(get_db), user: User = Depends(editor)):
    d = db.get(SiteDocument, slot)
    if not d:
        raise HTTPException(404, "No file")
    (settings.upload_dir / "docs" / f"{d.key}.pdf").unlink(missing_ok=True)
    db.delete(d)
    audit(db, user, "delete", "document", slot)
    db.commit()
