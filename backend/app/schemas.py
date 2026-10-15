import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import Image

Country = Literal["eg", "qa", "sa"]
ProjectType = Literal["residential", "hospitality", "retail", "office", "industrial", "healthcare", "public", "education"]
Service = Literal["contracting", "fitout", "supply", "pm", "unsure"]
ContactMethod = Literal["phone", "whatsapp", "email"]
EnquiryStatus = Literal["new", "contacted", "closed"]

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class ImageOut(BaseModel):
    src: str
    srcset: str
    width: int
    height: int
    color: str


def image_out(img: Image | None) -> ImageOut | None:
    if img is None:
        return None
    widths = [int(x) for x in img.widths.split(",")]
    mid = widths[min(1, len(widths) - 1)]
    return ImageOut(
        src=f"/media/{img.key}/{mid}.webp",
        srcset=", ".join(f"/media/{img.key}/{w}.webp {w}w" for w in widths),
        width=img.width,
        height=img.height,
        color=img.color,
    )


class ProjectImageOut(BaseModel):
    id: int
    is_cover: bool
    is_render: bool
    full_bleed: bool
    caption_en: str
    caption_ar: str
    sort_order: int
    image: ImageOut


class ProjectCardOut(BaseModel):
    id: int
    slug: str
    title_en: str
    title_ar: str
    city_en: str
    city_ar: str
    country: Country
    type: ProjectType
    year: int | None
    is_render: bool
    featured: bool
    cover: ImageOut | None


class ProjectDetailOut(ProjectCardOut):
    summary_en: str
    summary_ar: str
    area_m2: float | None
    scope_en: str
    scope_ar: str
    gallery: list[ProjectImageOut]
    related: list[ProjectCardOut]


class ClientOut(BaseModel):
    id: int
    name: str
    url: str
    logo: ImageOut | None


class OfficeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    country: Country
    address_en: str
    address_ar: str
    phone: str
    whatsapp: str
    email: str
    hours_en: str
    hours_ar: str
    maps_url: str


class SiteImageOut(BaseModel):
    slot: str
    alt_en: str
    alt_ar: str
    image: ImageOut


class BootstrapOut(BaseModel):
    offices: list[OfficeOut]
    site_images: dict[str, SiteImageOut]
    clients: list[ClientOut]
    projects: list[ProjectCardOut]


class EnquiryIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=40)
    email: str = Field(default="", max_length=200)
    country: Country
    service: Service
    project_type: ProjectType | Literal[""] = ""
    area_m2: float | None = Field(default=None, ge=0, le=1_000_000)
    message: str = Field(default="", max_length=4000)
    contact_method: ContactMethod = "whatsapp"
    lang: Literal["en", "ar"] = "en"
    consent: bool
    website: str = Field(default="", max_length=200)  # honeypot: real users leave it empty

    @field_validator("name", "message", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        v = v.strip()
        digits = re.sub(r"\D", "", v)
        if not (7 <= len(digits) <= 16) or not re.fullmatch(r"[+\d\s\-()]+", v):
            raise ValueError("invalid phone")
        return v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip()
        if v and not EMAIL_RE.match(v):
            raise ValueError("invalid email")
        return v

    @field_validator("consent")
    @classmethod
    def _consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("consent required")
        return v


# ---------- admin ----------
class LoginIn(BaseModel):
    email: str
    password: str = Field(max_length=200)


class ProjectIn(BaseModel):
    slug: str | None = Field(default=None, max_length=120)
    title_en: str = Field(min_length=1, max_length=200)
    title_ar: str = Field(default="", max_length=200)
    summary_en: str = Field(default="", max_length=2000)
    summary_ar: str = Field(default="", max_length=2000)
    city_en: str = Field(default="", max_length=100)
    city_ar: str = Field(default="", max_length=100)
    country: Country
    type: ProjectType
    year: int | None = Field(default=None, ge=1950, le=2100)
    area_m2: float | None = Field(default=None, ge=0, le=10_000_000)
    scope_en: str = Field(default="", max_length=300)
    scope_ar: str = Field(default="", max_length=300)
    is_render: bool = False
    featured: bool = True
    published: bool = True
    sort_order: int = 0


class ProjectAdminOut(ProjectIn):
    id: int
    slug: str
    cover: ImageOut | None
    images: list[ProjectImageOut]


class ProjectImagePatch(BaseModel):
    is_cover: bool | None = None
    is_render: bool | None = None
    full_bleed: bool | None = None
    caption_en: str | None = Field(default=None, max_length=300)
    caption_ar: str | None = Field(default=None, max_length=300)
    sort_order: int | None = None


class ClientIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    url: str = Field(default="", max_length=300)
    published: bool = True
    sort_order: int = 0


class ClientAdminOut(ClientIn):
    id: int
    logo: ImageOut | None


class OfficeIn(BaseModel):
    address_en: str = Field(default="", max_length=400)
    address_ar: str = Field(default="", max_length=400)
    phone: str = Field(default="", max_length=40)
    whatsapp: str = Field(default="", max_length=40)
    email: str = Field(default="", max_length=200)
    hours_en: str = Field(default="", max_length=200)
    hours_ar: str = Field(default="", max_length=200)
    maps_url: str = Field(default="", max_length=500)


class SiteImageAltIn(BaseModel):
    alt_en: str = Field(default="", max_length=300)
    alt_ar: str = Field(default="", max_length=300)


class EnquiryAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    name: str
    phone: str
    email: str
    country: Country
    service: str
    project_type: str
    area_m2: float | None
    message: str
    contact_method: str
    lang: str
    status: EnquiryStatus


class EnquiryStatusIn(BaseModel):
    status: EnquiryStatus
