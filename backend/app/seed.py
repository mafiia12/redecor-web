import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import Client, Office, Project, User
from .security import hash_password

log = logging.getLogger("redecor")

# Placeholders mirror the design: nothing is invented, everything is marked "[...]" until real data is entered.
# Egypt and Qatar currently share the same contact details (confirmed by the client).
_SHARED = dict(
    phone="+20 10 06602371",
    whatsapp="+20 10 06602371",
    email="info@redecorgroup.com",
    maps_url="https://www.google.com/maps?q=30.057389,31.199167",
    hours_en="[Days · Hours]",
    hours_ar="[الأيام · الساعات]",
)
ADDR_EN = "14 Abdel Qawy Ahmed St., off Shehab St.\nMohandessin, Giza, Egypt"
ADDR_AR = "١٤ شارع عبد القوي أحمد، متفرع من شارع شهاب\nالمهندسين، الجيزة، مصر"
OFFICES = {
    "eg": dict(address_en=ADDR_EN, address_ar=ADDR_AR, **_SHARED),
    "qa": dict(address_en="[Street, zone]\n[City], Qatar", address_ar="[الشارع، المنطقة]\n[المدينة]، قطر", **_SHARED),
}

# (country, type, is_render) in the order used by the design
DEMO_PROJECTS = [
    ("eg", "residential", False),
    ("qa", "hospitality", False),
    ("eg", "office", True),
    ("qa", "residential", False),
    ("eg", "retail", False),
    ("eg", "hospitality", True),
    ("qa", "retail", False),
    ("eg", "residential", False),
    ("qa", "residential", True),
]


def seed(db: Session) -> None:
    for country, vals in OFFICES.items():
        office = db.get(Office, country)
        if not office:
            db.add(Office(country=country, **vals))
            continue
        # Fill fields that are still empty or "[placeholders]"; never overwrite real values edited in the admin.
        for field, value in vals.items():
            current = getattr(office, field)
            if not current or current.startswith("["):
                setattr(office, field, value)

    if settings.admin_email and settings.admin_password:
        if not db.scalar(select(User).where(User.email == settings.admin_email)):
            db.add(User(email=settings.admin_email, password_hash=hash_password(settings.admin_password)))
            log.info("Created admin user %s", settings.admin_email)
    elif not db.scalar(select(User)):
        log.warning("No admin user: set ADMIN_EMAIL and ADMIN_PASSWORD, then restart.")

    if settings.seed_demo and not db.scalar(select(Project)):
        for i, (country, ptype, render) in enumerate(DEMO_PROJECTS, start=1):
            n = f"{i:02d}"
            db.add(
                Project(
                    slug=f"project-{n}",
                    title_en=f"[Project name {n}]",
                    title_ar=f"[اسم المشروع {n}]",
                    summary_en="[One-line summary of the project and the client’s brief.]",
                    summary_ar="[ملخص من سطر واحد عن المشروع وطلب العميل.]",
                    city_en="[Egypt city]" if country == "eg" else "[Qatar city]",
                    city_ar="[مدينة في مصر]" if country == "eg" else "[مدينة في قطر]",
                    country=country,
                    type=ptype,
                    scope_en="[Scope of work]",
                    scope_ar="[نطاق العمل]",
                    is_render=render,
                    sort_order=i,
                )
            )
    if settings.seed_demo and not db.scalar(select(Client)):
        for i in range(1, 13):
            db.add(Client(name=f"[Client {i:02d}]", sort_order=i))
    db.commit()
