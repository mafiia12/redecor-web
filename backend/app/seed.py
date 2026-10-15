import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import Client, Office, Project, User
from .security import hash_password

log = logging.getLogger("redecor")

# Placeholders mirror the design: nothing is invented, everything is marked "[...]" until real data is entered.
OFFICES = {
    "eg": dict(
        address_en="[Street, district]\n[City], Egypt",
        address_ar="[الشارع، الحي]\n[المدينة]، مصر",
        phone="[+20 XXX XXX XXXX]",
        whatsapp="",
        email="[name@domain.com]",
        hours_en="[Days · Hours]",
        hours_ar="[الأيام · الساعات]",
    ),
    "qa": dict(
        address_en="[Street, zone]\n[City], Qatar",
        address_ar="[الشارع، المنطقة]\n[المدينة]، قطر",
        phone="[+974 XXXX XXXX]",
        whatsapp="",
        email="[name@domain.com]",
        hours_en="[Days · Hours]",
        hours_ar="[الأيام · الساعات]",
    ),
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
        if not db.get(Office, country):
            db.add(Office(country=country, **vals))

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
