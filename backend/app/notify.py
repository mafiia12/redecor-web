"""E-mail notification for new enquiries.

Delivery is tracked on the enquiry row (notify_status / notify_attempts / notify_error / notified_at):
  pending -> sending -> sent
                     -> failed          (retried later, up to NOTIFY_MAX_ATTEMPTS)
  not_configured                        (SMTP env missing; picked up automatically once it is configured)
A row is "claimed" with an atomic UPDATE before sending, so two workers can never send the same enquiry twice.
"sent" is only recorded after the SMTP server accepted the message."""

import logging
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from sqlalchemy import or_, select, update

from .alerts import alert
from .config import settings
from .db import SessionLocal
from .models import Enquiry

log = logging.getLogger("redecor.notify")

SERVICE_LABELS = {
    "contracting": "Contracting",
    "fitout": "Interior Fit-Out",
    "supply": "Procurement & Supply",
    "pm": "Project Management",
    "unsure": "Not sure yet",
}
COUNTRY_LABELS = {"eg": "Egypt", "qa": "Qatar", "sa": "Saudi Arabia"}
STALE_SENDING = timedelta(minutes=15)


def build_message(e: Enquiry) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = f"New enquiry #{e.id}: {e.name} ({SERVICE_LABELS.get(e.service, e.service)}, {COUNTRY_LABELS.get(e.country, e.country)})"
    msg["From"] = formataddr(("Redecor website", settings.mail_from))
    msg["To"] = ", ".join(settings.notify_to)
    msg["Message-ID"] = make_msgid(idstring=f"enquiry-{e.id}")
    if e.email:
        msg["Reply-To"] = e.email
    lines = [
        f"Name: {e.name}",
        f"Phone: {e.phone}",
        f"E-mail: {e.email or '-'}",
        f"Preferred contact: {e.contact_method}",
        f"Country: {COUNTRY_LABELS.get(e.country, e.country)}",
        f"Service: {SERVICE_LABELS.get(e.service, e.service)}",
        f"Project type: {e.project_type or '-'}",
        f"Approx. area: {f'{e.area_m2:g} m2' if e.area_m2 else '-'}",
        f"Language: {e.lang}",
        f"Received: {e.created_at:%Y-%m-%d %H:%M} UTC" if e.created_at else "",
        "",
        "Message:",
        e.message or "-",
        "",
        f"Open the admin to follow up: {settings.site_url}/admin/enquiries",
    ]
    msg.set_content("\n".join(lines))
    return msg


def send(msg: EmailMessage) -> None:
    """Hand the message to the configured SMTP server. Raises on any failure."""
    ctx = ssl.create_default_context()
    if settings.smtp_security == "ssl":
        server: smtplib.SMTP = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20, context=ctx)
    else:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
    try:
        server.ehlo()
        if settings.smtp_security == "starttls":
            server.starttls(context=ctx)
            server.ehlo()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        refused = server.send_message(msg)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)
    finally:
        try:
            server.quit()
        except Exception:  # noqa: BLE001
            server.close()


def _safe_error(exc: Exception) -> str:
    text = f"{type(exc).__name__}: {exc}"
    if settings.smtp_password:
        text = text.replace(settings.smtp_password, "***")
    return text[:290]


def deliver(enquiry_id: int) -> str:
    """Try to notify about one enquiry. Returns the resulting notify_status."""
    with SessionLocal() as db:
        if not settings.smtp_configured:
            db.execute(
                update(Enquiry)
                .where(Enquiry.id == enquiry_id, Enquiry.notify_status == "pending")
                .values(notify_status="not_configured", notify_error="SMTP is not configured")
            )
            db.commit()
            return "not_configured"
        claimed = db.execute(
            update(Enquiry)
            .where(
                Enquiry.id == enquiry_id,
                Enquiry.notify_status.in_(("pending", "failed", "not_configured")),
                Enquiry.notify_attempts < settings.notify_max_attempts,
            )
            .values(notify_status="sending", notify_attempts=Enquiry.notify_attempts + 1, notified_at=datetime.now(timezone.utc))  # claim time while sending
        ).rowcount
        db.commit()
        if not claimed:
            row = db.get(Enquiry, enquiry_id)
            return row.notify_status if row else "missing"
        e = db.get(Enquiry, enquiry_id)
        try:
            send(build_message(e))
        except Exception as exc:  # noqa: BLE001
            e.notify_status, e.notify_error, e.notified_at = "failed", _safe_error(exc), None
            db.commit()
            log.error("Enquiry %s notification failed (attempt %s): %s", e.id, e.notify_attempts, e.notify_error)
            if e.notify_attempts >= settings.notify_max_attempts:
                alert("notification-failed", f"Enquiry #{e.id} could not be e-mailed after {e.notify_attempts} attempts. Check SMTP settings and the admin.")
            return "failed"
        e.notify_status, e.notify_error, e.notified_at = "sent", "", datetime.now(timezone.utc)
        db.commit()
        log.info("Enquiry %s notification sent", e.id)
        return "sent"


def retry_pending() -> int:
    """Retry failed / not-yet-configured / stuck notifications. Returns how many were attempted."""
    if not settings.smtp_configured:
        return 0
    stale = datetime.now(timezone.utc) - STALE_SENDING
    with SessionLocal() as db:
        # A crash between "sending" and "sent" leaves the row stuck; re-queue it (a rare duplicate beats a lost lead).
        db.execute(
            update(Enquiry)
            .where(Enquiry.notify_status == "sending", Enquiry.notified_at < stale)
            .values(notify_status="failed", notify_error="Interrupted while sending")
        )
        db.commit()
        ids = db.scalars(
            select(Enquiry.id).where(
                or_(Enquiry.notify_status.in_(("pending", "failed", "not_configured"))),
                Enquiry.notify_attempts < settings.notify_max_attempts,
            )
        ).all()
    for i in ids:
        deliver(i)
    return len(ids)
