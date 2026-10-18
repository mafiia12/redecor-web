"""Single source of truth for what the PUBLIC site may show. Admin endpoints see everything."""

from sqlalchemy import and_, not_

from .config import settings
from .models import Client, Office, Project, SiteDocument, Testimonial

TEST_SLUG_PREFIX = "test-project-"


def is_placeholder(text: str | None) -> bool:
    """Unfinished content is written as "[Like this]" in seeds and drafts."""
    return bool(text) and "[" in text and "]" in text


def public_projects():
    """SQL filter: published, no "[placeholder]" title, and TEST data hidden unless ALLOW_TEST_CONTENT=1."""
    clauses = [Project.published.is_(True), not_(Project.title_en.contains("["))]
    if not settings.allow_test_content:
        clauses.append(not_(Project.slug.startswith(TEST_SLUG_PREFIX)))
    return and_(*clauses)


def public_clients():
    """A client appears only when published, with a real name and an uploaded logo."""
    return and_(Client.published.is_(True), Client.logo_image_id.is_not(None), not_(Client.name.contains("[")))


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
