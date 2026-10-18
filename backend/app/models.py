from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # admin: everything incl. users and offices · editor: content · viewer: read-only
    role: Mapped[str] = mapped_column(String(10), default="admin", server_default="admin")
    # Bumped on password change / revoke: every older session token stops working.
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Image(Base):
    """A processed upload. Variants live on disk at <upload_dir>/<key>/<width>.webp."""

    __tablename__ = "images"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(32), unique=True)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    widths: Mapped[str] = mapped_column(String(100))  # "480,960,1600"
    color: Mapped[str] = mapped_column(String(7), default="#E4E1DB")  # average colour for placeholders
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title_en: Mapped[str] = mapped_column(String(200))
    title_ar: Mapped[str] = mapped_column(String(200), default="")
    summary_en: Mapped[str] = mapped_column(Text, default="")
    summary_ar: Mapped[str] = mapped_column(Text, default="")
    city_en: Mapped[str] = mapped_column(String(100), default="")
    city_ar: Mapped[str] = mapped_column(String(100), default="")
    country: Mapped[str] = mapped_column(String(2), index=True)  # eg | qa
    type: Mapped[str] = mapped_column(String(20), index=True)  # residential | hospitality | retail | office
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    scope_en: Mapped[str] = mapped_column(String(300), default="")
    scope_ar: Mapped[str] = mapped_column(String(300), default="")
    tagline_en: Mapped[str] = mapped_column(String(300), default="", server_default="")
    tagline_ar: Mapped[str] = mapped_column(String(300), default="", server_default="")
    # Long-form text for the project page. Blank line = new paragraph; a line starting with "## " is a heading.
    story_en: Mapped[str] = mapped_column(Text, default="", server_default="")
    story_ar: Mapped[str] = mapped_column(Text, default="", server_default="")
    # One "Label: Value" per line (Client: ..., Area: ...), shown as a facts list on the project page.
    details_en: Mapped[str] = mapped_column(Text, default="", server_default="")
    details_ar: Mapped[str] = mapped_column(Text, default="", server_default="")
    client_name: Mapped[str] = mapped_column(String(200), default="", server_default="")
    logo_image_id: Mapped[int | None] = mapped_column(ForeignKey("images.id"), nullable=True)
    is_render: Mapped[bool] = mapped_column(Boolean, default=False)
    featured: Mapped[bool] = mapped_column(Boolean, default=True)
    published: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    logo: Mapped["Image | None"] = relationship(foreign_keys=[logo_image_id], lazy="joined")
    images: Mapped[list["ProjectImage"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectImage.sort_order, ProjectImage.id",
    )


class ProjectImage(Base):
    __tablename__ = "project_images"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id"))
    is_cover: Mapped[bool] = mapped_column(Boolean, default=False)
    is_render: Mapped[bool] = mapped_column(Boolean, default=False)
    full_bleed: Mapped[bool] = mapped_column(Boolean, default=False)
    layout: Mapped[str] = mapped_column(String(8), default="full", server_default="full")  # full | half
    caption_en: Mapped[str] = mapped_column(String(300), default="")
    caption_ar: Mapped[str] = mapped_column(String(300), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    project: Mapped[Project] = relationship(back_populates="images")
    image: Mapped[Image] = relationship(lazy="joined")


class Client(Base):
    __tablename__ = "clients"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(300), default="")
    logo_image_id: Mapped[int | None] = mapped_column(ForeignKey("images.id"), nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)

    logo: Mapped[Image | None] = relationship(lazy="joined")


class SiteImage(Base):
    """Named image slots used across the site (hero, services, how-we-work...)."""

    __tablename__ = "site_images"
    slot: Mapped[str] = mapped_column(String(60), primary_key=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id"))
    alt_en: Mapped[str] = mapped_column(String(300), default="")
    alt_ar: Mapped[str] = mapped_column(String(300), default="")

    image: Mapped[Image] = relationship(lazy="joined")


class Office(Base):
    __tablename__ = "offices"
    country: Mapped[str] = mapped_column(String(2), primary_key=True)  # eg | qa
    address_en: Mapped[str] = mapped_column(String(400), default="")
    address_ar: Mapped[str] = mapped_column(String(400), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    whatsapp: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    hours_en: Mapped[str] = mapped_column(String(200), default="")
    hours_ar: Mapped[str] = mapped_column(String(200), default="")
    maps_url: Mapped[str] = mapped_column(String(500), default="")


class Enquiry(Base):
    __tablename__ = "enquiries"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(40))
    email: Mapped[str] = mapped_column(String(200), default="")
    country: Mapped[str] = mapped_column(String(2))
    service: Mapped[str] = mapped_column(String(30))
    project_type: Mapped[str] = mapped_column(String(20), default="")
    area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    message: Mapped[str] = mapped_column(Text, default="")
    contact_method: Mapped[str] = mapped_column(String(10), default="whatsapp")
    lang: Mapped[str] = mapped_column(String(2), default="en")
    status: Mapped[str] = mapped_column(String(12), default="new", index=True)  # new | contacted | closed
    # E-mail notification: pending | sending | sent | failed | not_configured | legacy (rows older than the feature)
    notify_status: Mapped[str] = mapped_column(String(16), default="pending", server_default="legacy", index=True)
    notify_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    notify_error: Mapped[str] = mapped_column(String(300), default="", server_default="")
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Hash of the submitted content: the same enquiry sent twice within minutes is stored once.
    fingerprint: Mapped[str] = mapped_column(String(64), default="", server_default="", index=True)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    user_email: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(40))
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(80), default="")


class AnalyticsDaily(Base):
    """Privacy-friendly counters: one row per (day, event, path, lang). No cookies, IPs or personal data."""

    __tablename__ = "analytics_daily"
    __table_args__ = (UniqueConstraint("day", "name", "path", "lang"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    name: Mapped[str] = mapped_column(String(40))
    path: Mapped[str] = mapped_column(String(200), default="")
    lang: Mapped[str] = mapped_column(String(2), default="")
    count: Mapped[int] = mapped_column(Integer, default=0)


class Testimonial(Base):
    """Shown publicly only when published AND the client's written approval is recorded."""

    __tablename__ = "testimonials"
    id: Mapped[int] = mapped_column(primary_key=True)
    quote_en: Mapped[str] = mapped_column(Text, default="")
    quote_ar: Mapped[str] = mapped_column(Text, default="")
    author: Mapped[str] = mapped_column(String(120))
    role_en: Mapped[str] = mapped_column(String(160), default="")
    role_ar: Mapped[str] = mapped_column(String(160), default="")
    company: Mapped[str] = mapped_column(String(160), default="")
    approval_note: Mapped[str] = mapped_column(String(300), default="")  # e.g. "Approved by e-mail 2026-11-02"
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SiteDocument(Base):
    """Downloadable files such as the company profile PDF (slot = "company-profile")."""

    __tablename__ = "site_documents"
    slot: Mapped[str] = mapped_column(String(40), primary_key=True)
    key: Mapped[str] = mapped_column(String(32), unique=True)
    filename: Mapped[str] = mapped_column(String(160))
    size: Mapped[int] = mapped_column(Integer)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
