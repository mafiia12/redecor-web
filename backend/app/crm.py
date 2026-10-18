"""Enquiries CRM: status workflow, append-only history, follow-ups, and the daily digest e-mail.

Status workflow:  new -> contacted -> quoted -> won | lost      (spam from any open status)
"closed" is the status used before this feature; such rows keep it and can move to any status.
A finished enquiry (won / lost / spam) can be reopened to "contacted".
"""

import logging
from datetime import date, datetime, time, timedelta, timezone
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal
from .models import Enquiry, EnquiryEvent, JobRun, User

log = logging.getLogger("redecor.crm")

STATUSES = ["new", "contacted", "quoted", "won", "lost", "spam"]
LEGACY = {"closed"}
FINISHED = {"won", "lost", "spam", "closed"}
TRANSITIONS: dict[str, set[str]] = {
    "new": {"contacted", "quoted", "lost", "spam"},
    "contacted": {"quoted", "won", "lost", "spam"},
    "quoted": {"won", "lost", "spam", "contacted"},
    "won": {"contacted"},
    "lost": {"contacted"},
    "spam": {"contacted", "new"},
    "closed": set(STATUSES),
}


def tz() -> ZoneInfo:
    try:
        return ZoneInfo(settings.digest_tz or "Africa/Cairo")
    except ZoneInfoNotFoundError:
        return ZoneInfo("Africa/Cairo")


def today() -> date:
    return datetime.now(tz()).date()


def is_overdue(e: Enquiry, on: date | None = None) -> bool:
    return bool(e.next_follow_up and e.status not in FINISHED and e.next_follow_up < (on or today()))


def overdue_clause(on: date | None = None):
    return (Enquiry.next_follow_up.is_not(None)) & (Enquiry.next_follow_up < (on or today())) & Enquiry.status.not_in(FINISHED)


def record(db: Session, e: Enquiry, user: User, kind: str, before: object = "", after: object = "", note: str = "") -> None:
    db.add(EnquiryEvent(enquiry_id=e.id, user_email=user.email, kind=kind, from_value=str(before or "")[:60],
                        to_value=str(after or "")[:60], note=note))


# ---------- daily digest ----------
JOB = "daily-digest"


def digest_data(db: Session, on: date | None = None) -> dict:
    on = on or today()
    start = datetime.combine(on - timedelta(days=1), time(0), tz()).astimezone(timezone.utc)
    end = datetime.combine(on, time(0), tz()).astimezone(timezone.utc)
    new = db.scalars(select(Enquiry).where(Enquiry.created_at >= start, Enquiry.created_at < end, Enquiry.status != "spam")
                     .order_by(Enquiry.created_at)).all()
    overdue = db.scalars(select(Enquiry).where(overdue_clause(on)).order_by(Enquiry.next_follow_up)).all()
    due = db.scalars(select(Enquiry).where(Enquiry.next_follow_up == on, Enquiry.status.not_in(FINISHED))).all()
    open_counts = dict(db.execute(select(Enquiry.status, func.count()).where(Enquiry.status.not_in(FINISHED))
                                  .group_by(Enquiry.status)).all())
    users = {u.id: u.email for u in db.scalars(select(User))}
    return {"day": on, "new": new, "overdue": overdue, "due_today": due, "open": open_counts, "users": users}


def _line(e: Enquiry, users: dict) -> str:
    files = len(e.attachments)
    who = users.get(e.assigned_to_id, "unassigned")
    follow = f", follow-up {e.next_follow_up:%Y-%m-%d}" if e.next_follow_up else ""
    att = f", {files} attachment{'s' if files != 1 else ''}" if files else ""
    return f"  #{e.id} {e.name} [{e.status}] {e.service}/{e.country} ({e.lang}), {who}{follow}{att}"


def digest_text(d: dict) -> str:
    users = d["users"]
    parts = [f"Enquiries digest for {d['day']:%Y-%m-%d} ({settings.digest_tz})", ""]
    for title, rows in (("New in the last day", d["new"]), ("Overdue follow-ups", d["overdue"]), ("Follow-ups due today", d["due_today"])):
        parts.append(f"{title}: {len(rows)}")
        parts += [_line(e, users) for e in rows[:50]]
        if len(rows) > 50:
            parts.append(f"  ... and {len(rows) - 50} more")
        parts.append("")
    if d["open"]:
        parts.append("Open by status: " + ", ".join(f"{k} {v}" for k, v in sorted(d["open"].items())))
    parts += ["", "Files are never attached to this e-mail. Open the admin to see them:", f"{settings.site_url}/admin/enquiries"]
    return "\n".join(parts)


def digest_message(d: dict) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = f"Enquiries digest {d['day']:%Y-%m-%d}: {len(d['new'])} new, {len(d['overdue'])} overdue"
    msg["From"] = formataddr(("Redecor website", settings.mail_from))
    msg["To"] = ", ".join(settings.notify_to)
    msg["Message-ID"] = make_msgid(idstring=f"digest-{d['day']:%Y%m%d}")
    msg.set_content(digest_text(d))
    return msg


def _claim(db: Session, day: str) -> bool:
    """Atomically mark today's digest as taken, so restarts or two workers never send it twice."""
    if db.get(JobRun, JOB) is None:
        try:
            db.add(JobRun(name=JOB, last_run="", last_status=""))
            db.commit()
        except IntegrityError:
            db.rollback()
    claimed = db.execute(update(JobRun).where(JobRun.name == JOB, JobRun.last_run != day)
                         .values(last_run=day, last_status="sending")).rowcount
    db.commit()
    return bool(claimed)


def run_digest(dry_run: bool = False, force: bool = False, on: date | None = None) -> str:
    """Build and send the digest. Returns: printed text (dry run) | sent | skipped:<reason> | failed:<reason>."""
    from .notify import _safe_error, send

    on = on or today()
    with SessionLocal() as db:
        d = digest_data(db, on)
        if dry_run:
            return digest_text(d)
        day = on.isoformat()
        if force:
            _claim(db, day)
            db.execute(update(JobRun).where(JobRun.name == JOB).values(last_run=day))
            db.commit()
        elif not _claim(db, day):
            return "skipped:already-sent"
        if not settings.smtp_configured:  # logged once per day (the day is claimed), never an error
            log.warning("Daily digest skipped: SMTP is not configured (SMTP_HOST, MAIL_FROM, NOTIFY_TO)")
            db.execute(update(JobRun).where(JobRun.name == JOB).values(last_status="skipped: SMTP not configured"))
            db.commit()
            return "skipped:smtp-not-configured"
        try:
            send(digest_message(d))
        except Exception as exc:  # noqa: BLE001
            err = _safe_error(exc)
            # not retried the same day (no e-mail storm on a broken SMTP); the admin System page shows it
            db.execute(update(JobRun).where(JobRun.name == JOB).values(last_status=f"failed: {err}"[:200]))
            db.commit()
            log.error("Daily digest failed: %s", err)
            return f"failed:{err}"
        db.execute(update(JobRun).where(JobRun.name == JOB).values(last_status=f"sent {datetime.now(timezone.utc):%H:%M} UTC"))
        db.commit()
        log.info("Daily digest sent for %s", day)
        return "sent"


def digest_pending(on: date | None = None) -> bool:
    """Cheap check before the claim: has today's digest not been taken yet?"""
    with SessionLocal() as db:
        row = db.get(JobRun, JOB)
        return row is None or row.last_run != (on or today()).isoformat()


def digest_due(now: datetime | None = None) -> bool:
    """True once the local time has passed DIGEST_TIME today (the claim then prevents a second send)."""
    if not settings.digest_time:
        return False
    try:
        hh, mm = (int(x) for x in settings.digest_time.split(":", 1))
    except ValueError:
        return False
    now = (now or datetime.now(timezone.utc)).astimezone(tz())
    return (now.hour, now.minute) >= (hh, mm)
