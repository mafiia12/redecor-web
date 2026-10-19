"""Enquiries CRM (admin only: enquiries hold personal data). Status workflow, assignment, follow-ups,
internal notes, append-only history, filters, export, attachment downloads, and the digest preview."""

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import crm, private_files, sheets
from ..config import settings
from ..db import get_db
from ..models import Enquiry, EnquiryAttachment, EnquiryEvent, User
from ..notify import deliver
from ..schemas import EnquiryAdminOut, EnquiryAttachmentOut, EnquiryDetailOut, EnquiryEventOut, EnquiryPatch
from ..security import admin_only
from .admin import audit

router = APIRouter(prefix="/api/admin", tags=["admin"])

EXPORT_COLUMNS = ["id", "received", "status", "name", "phone", "email", "country", "service", "project_type", "area_m2",
                  "contact_method", "language", "source_page", "assigned_to", "next_follow_up", "overdue", "attachments",
                  "message"]


def _users(db: Session) -> dict[int, str]:
    return {u.id: u.email for u in db.scalars(select(User))}


def _out(e: Enquiry, users: dict[int, str], on: date) -> dict:
    base = EnquiryAdminOut.model_validate(e).model_dump()
    base.update(assigned_to=users.get(e.assigned_to_id, "") if e.assigned_to_id else "", source_page=e.source_page or "",
                overdue=crm.is_overdue(e, on), attachment_count=len(e.attachments),
                next_statuses=[s for s in crm.STATUSES if s in crm.TRANSITIONS.get(e.status, set())])
    return base


def _get(db: Session, eid: int) -> Enquiry:
    e = db.get(Enquiry, eid)
    if not e:
        raise HTTPException(404, "Enquiry not found")
    return e


def _detail(db: Session, e: Enquiry) -> EnquiryDetailOut:
    events = db.scalars(select(EnquiryEvent).where(EnquiryEvent.enquiry_id == e.id).order_by(EnquiryEvent.id.desc()))
    return EnquiryDetailOut(
        **_out(e, _users(db), crm.today()),
        events=[EnquiryEventOut.model_validate(x) for x in events],
        attachments=[EnquiryAttachmentOut(id=a.id, original_name=a.original_name, size=a.size, detected_type=a.detected_type,
                                          scan_status=a.scan_status, scan_detail=a.scan_detail) for a in e.attachments],
    )


@router.get("/enquiries")
def list_enquiries(
    status: str = "", assignee: str = "", overdue: bool = False, date_from: date | None = None, date_to: date | None = None,
    lang: str = "", q: str = "", format: str = "json", db: Session = Depends(get_db), user: User = Depends(admin_only),
):
    """Filters: status (comma list, or 'open'), assignee (user id, 'me' or 'none'), overdue, received date range (local
    time zone), language, free-text search on name / phone / e-mail / message. format=csv|xlsx exports the same rows."""
    stmt = select(Enquiry)
    if status == "open":
        stmt = stmt.where(Enquiry.status.not_in(crm.FINISHED))
    elif status:
        stmt = stmt.where(Enquiry.status.in_([s for s in status.split(",") if s]))
    if assignee == "none":
        stmt = stmt.where(Enquiry.assigned_to_id.is_(None))
    elif assignee == "me":
        stmt = stmt.where(Enquiry.assigned_to_id == user.id)
    elif assignee.isdigit():
        stmt = stmt.where(Enquiry.assigned_to_id == int(assignee))
    if overdue:
        stmt = stmt.where(crm.overdue_clause())
    if date_from:
        stmt = stmt.where(Enquiry.created_at >= datetime.combine(date_from, time(0), crm.tz()))
    if date_to:
        stmt = stmt.where(Enquiry.created_at < datetime.combine(date_to + timedelta(days=1), time(0), crm.tz()))
    if lang in ("en", "ar"):
        stmt = stmt.where(Enquiry.lang == lang)
    if q.strip():
        like = f"%{q.strip()[:100]}%"
        stmt = stmt.where(or_(Enquiry.name.ilike(like), Enquiry.phone.ilike(like), Enquiry.email.ilike(like),
                              Enquiry.message.ilike(like)))
    rows = db.scalars(stmt.order_by(Enquiry.created_at.desc()).limit(2000 if format in ("csv", "xlsx") else 500)).all()
    users, on = _users(db), crm.today()
    out = [_out(e, users, on) for e in rows]
    if format in ("csv", "xlsx"):
        audit(db, user, f"export:{format}", "enquiries", len(out))
        db.commit()
        flat = [{**r, "received": r["created_at"].astimezone(crm.tz()).strftime("%Y-%m-%d %H:%M"), "language": r["lang"],
                 "attachments": r["attachment_count"], "next_follow_up": r["next_follow_up"] or "",
                 "overdue": "yes" if r["overdue"] else ""} for r in out]
        return sheets.export(flat, EXPORT_COLUMNS, f"enquiries-{on:%Y%m%d}", format)
    return out


@router.get("/enquiries/assignees")
def assignees(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return [{"id": u.id, "email": u.email} for u in db.scalars(select(User).where(User.role == "admin").order_by(User.email))]


@router.get("/enquiries/digest-preview")
def digest_preview(_: User = Depends(admin_only)):
    return {"text": crm.run_digest(dry_run=True), "time": settings.digest_time, "tz": settings.digest_tz,
            "smtp_configured": settings.smtp_configured}


@router.get("/enquiries/{eid}", response_model=EnquiryDetailOut)
def get_enquiry(eid: int, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return _detail(db, _get(db, eid))


@router.patch("/enquiries/{eid}", response_model=EnquiryDetailOut)
def update_enquiry(eid: int, data: EnquiryPatch, db: Session = Depends(get_db), user: User = Depends(admin_only)):
    e = _get(db, eid)
    sent = data.model_fields_set
    note = data.note.strip()
    if "status" in sent and data.status and data.status != e.status:
        if data.status not in crm.TRANSITIONS.get(e.status, set()):
            raise HTTPException(422, f"An enquiry cannot go from '{e.status}' to '{data.status}'")
        crm.record(db, e, user, "status", e.status, data.status, note)
        note = ""  # the note explains the status change
        audit(db, user, f"status:{data.status}", "enquiry", eid)
        e.status = data.status
    if "assigned_to_id" in sent and data.assigned_to_id != e.assigned_to_id:
        users = _users(db)
        if data.assigned_to_id is not None:
            target = db.get(User, data.assigned_to_id)
            if not target or target.role != "admin":
                raise HTTPException(422, "Enquiries can only be assigned to an admin account")
        crm.record(db, e, user, "assign", users.get(e.assigned_to_id, ""), users.get(data.assigned_to_id, ""))
        e.assigned_to_id = data.assigned_to_id
    if "next_follow_up" in sent and data.next_follow_up != e.next_follow_up:
        crm.record(db, e, user, "follow_up", e.next_follow_up or "", data.next_follow_up or "")
        e.next_follow_up = data.next_follow_up
    if note:
        crm.record(db, e, user, "note", note=note)
    db.commit()
    return _detail(db, e)


@router.post("/enquiries/{eid}/notify", response_model=EnquiryAdminOut)
def resend_notification(eid: int, db: Session = Depends(get_db), user: User = Depends(admin_only)):
    """Retry the e-mail for one enquiry. An already delivered notification is never sent twice."""
    e = _get(db, eid)
    if e.notify_status == "sent":
        raise HTTPException(409, "This notification was already delivered")
    if e.notify_status in ("legacy",):
        e.notify_status = "pending"
    e.notify_attempts = min(e.notify_attempts, settings.notify_max_attempts - 1)  # allow one manual attempt
    db.commit()
    deliver(eid)
    db.expire_all()
    audit(db, user, "notify", "enquiry", eid)
    db.commit()
    return _out(_get(db, eid), _users(db), crm.today())


@router.get("/enquiries/{eid}/attachments/{aid}")
def download_attachment(eid: int, aid: int, db: Session = Depends(get_db), user: User = Depends(admin_only)):
    a = db.get(EnquiryAttachment, aid)
    if not a or a.enquiry_id != eid:
        raise HTTPException(404, "Attachment not found")
    if a.scan_status == "infected":
        raise HTTPException(409, "This file was flagged by the virus scanner and cannot be downloaded")
    audit(db, user, "download", "enquiry_attachment", aid)
    db.commit()
    return private_files.download("attachments", a.stored_name, a.original_name, a.detected_type)
