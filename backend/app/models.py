from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
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
    is_render: Mapped[bool] = mapped_column(Boolean, default=False)
    featured: Mapped[bool] = mapped_column(Boolean, default=True)
    published: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

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


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    user_email: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(40))
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(80), default="")
