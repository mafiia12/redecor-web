"""Server-side <head> for every public URL.

Social crawlers (WhatsApp, Facebook, LinkedIn, X) and some search bots do not run JavaScript, so the SPA's
client-side titles never reach them. The server therefore answers each URL with index.html whose <head> already
carries the page's own title, description, canonical URL, hreflang alternates, Open Graph tags and JSON-LD, and
with the correct HTTP status (404 for unknown pages and unpublished projects)."""

import json
import re
from dataclasses import dataclass, field
from html import escape

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import Office, Project
from .serializers import cover_of
from .visibility import clean_office, public_projects

BRAND = {"en": "RE DECOR & MORE", "ar": "ريديكور آند مور"}
HOME = {
    "en": ("RE DECOR & MORE | Interior design, fit-out and supply in Egypt and Qatar",
           "Design, fit-out and supply for homes, hospitality and business across Egypt and Qatar."),
    "ar": ("ريديكور آند مور | تصميم داخلي وتنفيذ وتوريد في مصر وقطر",
           "تصميم وتنفيذ وتوريد للوحدات السكنية والفنادق والمشروعات التجارية في مصر وقطر."),
}
PAGES = {
    "/projects": {"en": ("Our Projects", "A showcase of craftsmanship, precision, and thoughtful execution."),
                  "ar": ("مشاريعنا", "عرض لأعمال تعكس الإتقان والدقة والتنفيذ المدروس.")},
    "/about": {"en": ("About REDECOR", "We Design It. We Build It. We Bring It to Life."),
               "ar": ("عن ريديكور", "نصمّمها. ننفّذها. ونحوّلها إلى واقع.")},
    "/contact": {"en": ("Contact", "Tell us about your next project."),
                 "ar": ("تواصل معنا", "أخبرنا عن مشروعك القادم.")},
    "/privacy": {"en": ("Privacy policy", ""), "ar": ("سياسة الخصوصية", "")},
    "/services/contracting": {"en": ("Contracting", "Built with precision."), "ar": ("المقاولات", "تُنفَّذ بدقة.")},
    "/services/fitout": {"en": ("Interior Fit-Out", "Crafted to perfection."),
                         "ar": ("التشطيبات الداخلية والتجهيز", "مصنوعة بإتقان.")},
    "/services/supply": {"en": ("Procurement & Supply", "Quality in every selection."),
                         "ar": ("المشتريات والتوريد", "الجودة في كل اختيار.")},
    "/services/project-management": {"en": ("Project Management", "Seamless from start to finish."),
                                     "ar": ("إدارة المشاريع", "بسلاسة من البداية إلى النهاية.")},
}
NOT_FOUND = {"en": "Page not found", "ar": "الصفحة غير موجودة"}


@dataclass
class Head:
    status: int
    title: str
    description: str = ""
    lang: str = "en"
    path: str = "/"  # language-neutral path, e.g. /projects/x
    image: str = ""
    og_type: str = "website"
    index: bool = True
    jsonld: list[dict] = field(default_factory=list)


def _abs(url: str) -> str:
    return url if url.startswith("http") else f"{settings.site_url}{url}"


def _url(lang: str, path: str) -> str:
    if lang == "ar":
        return _abs("/ar" if path == "/" else f"/ar{path}")
    return _abs(path)


def organization(db: Session) -> dict:
    """Only facts the company has confirmed: name, site, logo, e-mail, phone and social profiles."""
    org = {"@context": "https://schema.org", "@type": "Organization", "name": "Redecor Group",
           "alternateName": "RE DECOR & MORE", "url": settings.site_url, "logo": _abs("/logo-ink.svg")}
    eg = db.get(Office, "eg")
    if eg:
        o = clean_office(eg)
        if o["email"]:
            org["email"] = o["email"]
        if o["phone"]:
            org["telephone"] = o["phone"]
    if settings.social_links:
        org["sameAs"] = settings.social_links
    return org


def resolve(db: Session, raw_path: str) -> Head:
    path = "/" + raw_path.strip("/")
    lang = "en"
    if path == "/ar" or path.startswith("/ar/"):
        lang, path = "ar", path[3:] or "/"
    if path == "/":
        t, d = HOME[lang]
        return Head(200, t, d, lang, path, jsonld=[organization(db)])
    if path in PAGES:
        t, d = PAGES[path][lang]
        return Head(200, f"{t} | {BRAND[lang]}", d or HOME[lang][1], lang, path)
    m = re.fullmatch(r"/projects/([a-z0-9\-]{1,120})", path)
    if m:
        p = db.scalar(select(Project).where(Project.slug == m.group(1), public_projects()))
        if p:
            title = (p.title_ar if lang == "ar" and p.title_ar else p.title_en)
            desc = (p.summary_ar if lang == "ar" and p.summary_ar else p.summary_en) or (
                p.tagline_ar if lang == "ar" and p.tagline_ar else p.tagline_en) or HOME[lang][1]
            cover = cover_of(p)
            image = ""
            if cover:
                widths = [int(x) for x in cover.image.widths.split(",")]
                w = max([x for x in widths if x <= 1600] or widths)
                image = f"/media/{cover.image.key}/{w}.webp"
            crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": BRAND[lang], "item": _url(lang, "/")},
                {"@type": "ListItem", "position": 2, "name": PAGES["/projects"][lang][0], "item": _url(lang, "/projects")},
                {"@type": "ListItem", "position": 3, "name": title, "item": _url(lang, path)},
            ]}
            return Head(200, f"{title} | {BRAND[lang]}", desc[:300], lang, path, image, "article", jsonld=[crumbs])
    return Head(404, f"{NOT_FOUND[lang]} | {BRAND[lang]}", "", lang, path, index=False)


_STRIP = [
    re.compile(r"<title>.*?</title>", re.S),
    re.compile(r'<meta\s+name="description"[^>]*>', re.S),
    re.compile(r'<meta\s+property="og:(title|description|image|url|type|locale)"[^>]*>', re.S),
    re.compile(r'<meta\s+name="twitter:[^"]*"[^>]*>', re.S),
]


def render(template: str, head: Head) -> str:
    html = template
    for rx in _STRIP:
        html = rx.sub("", html)
    image = _abs(head.image or "/og-default.png")
    tags = [
        f"<title>{escape(head.title)}</title>",
        f'<meta name="description" content="{escape(head.description)}" />' if head.description else "",
        f'<meta property="og:title" content="{escape(head.title)}" />',
        f'<meta property="og:description" content="{escape(head.description)}" />' if head.description else "",
        f'<meta property="og:type" content="{head.og_type}" />',
        f'<meta property="og:image" content="{escape(image)}" />',
        f'<meta property="og:locale" content="{"ar_EG" if head.lang == "ar" else "en_US"}" />',
        '<meta name="twitter:card" content="summary_large_image" />',
    ]
    if head.index:
        canonical = _url(head.lang, head.path)
        tags += [
            f'<link rel="canonical" href="{escape(canonical)}" />',
            f'<meta property="og:url" content="{escape(canonical)}" />',
            f'<link rel="alternate" hreflang="en" href="{escape(_url("en", head.path))}" />',
            f'<link rel="alternate" hreflang="ar" href="{escape(_url("ar", head.path))}" />',
            f'<link rel="alternate" hreflang="x-default" href="{escape(_url("en", head.path))}" />',
        ]
    else:
        tags.append('<meta name="robots" content="noindex" />')
    for block in head.jsonld:
        data = json.dumps(block, ensure_ascii=False).replace("</", "<\\/")
        tags.append(f'<script type="application/ld+json">{data}</script>')
    html = html.replace("</head>", "    " + "\n    ".join(t for t in tags if t) + "\n  </head>", 1)
    # First paint in the right language and direction (React keeps them in sync afterwards).
    html = re.sub(r'<html lang="[a-z]+" dir="[a-z]+"', f'<html lang="{head.lang}" dir="{"rtl" if head.lang == "ar" else "ltr"}"', html, count=1)
    return html
