"""Single source of truth for what the PUBLIC site may show. Admin endpoints see everything."""

from sqlalchemy import and_, exists, not_
from sqlalchemy.orm import aliased

from .config import settings
from .models import Approval, Client, Office, Project, SiteDocument, Testimonial

TEST_SLUG_PREFIX = "test-project-"


def is_placeholder(text: str | None) -> bool:
    """Unfinished content is written as "[Like this]" in seeds and drafts."""
    return bool(text) and "[" in text and "]" in text


# What each kind of public item needs on record before it can be shown (Phase B2 publishing gate).
REQUIRED_APPROVAL = {"project": "client_permission_to_publish", "client": "logo_usage_permission"}
APPROVAL_TYPES = ("client_permission_to_publish", "logo_usage_permission", "photo_rights")
APPROVAL_STATUSES = ("pending", "approved", "rejected", "revoked")


def approved_clause(subject_type: str, id_column):
    """True when the NEWEST approval row of the required type for this subject is 'approved'."""
    a_type = REQUIRED_APPROVAL[subject_type]
    later = aliased(Approval)
    return exists().where(
        Approval.subject_type == subject_type, Approval.subject_id == id_column, Approval.approval_type == a_type,
        Approval.status == "approved",
        ~exists().where(later.subject_type == Approval.subject_type, later.subject_id == Approval.subject_id,
                        later.approval_type == Approval.approval_type, later.id > Approval.id),  # no newer row overrides it
    )


def public_projects(gate: bool | None = None):
    """SQL filter: published, no "[placeholder]" title, TEST data hidden unless ALLOW_TEST_CONTENT=1, and
    (ENFORCE_APPROVALS=1) a current approval to publish on record. gate=False: everything but the approval."""
    clauses = [Project.published.is_(True), not_(Project.title_en.contains("["))]
    if not settings.allow_test_content:
        clauses.append(not_(Project.slug.startswith(TEST_SLUG_PREFIX)))
    if settings.enforce_approvals if gate is None else gate:
        clauses.append(approved_clause("project", Project.id))
    return and_(*clauses)


def public_clients(gate: bool | None = None):
    """A client appears only when published, with a real name, an uploaded logo and (gate on) logo permission."""
    clauses = [Client.published.is_(True), Client.logo_image_id.is_not(None), not_(Client.name.contains("["))]
    if settings.enforce_approvals if gate is None else gate:
        clauses.append(approved_clause("client", Client.id))
    return and_(*clauses)


def public_testimonials():
    return and_(Testimonial.published.is_(True), Testimonial.approved.is_(True))


def public_documents():
    return SiteDocument.published.is_(True)


OFFICE_FIELDS = ("address_en", "address_ar", "phone", "whatsapp", "email", "hours_en", "hours_ar", "maps_url")


def clean_office(o: Office) -> dict:
    """Office as the public site sees it: placeholder values become empty strings (and are therefore hidden)."""
    data = {"country": o.country}
    for f in OFFICE_FIELDS:
        v = getattr(o, f) or ""
        data[f] = "" if is_placeholder(v) else v
    return data
