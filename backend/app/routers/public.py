import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Client, Enquiry, Office, Project, SiteImage
from ..schemas import BootstrapOut, EnquiryIn, ProjectDetailOut, SiteImageOut, image_out, OfficeOut
from ..security import RateLimiter, client_ip
from ..serializers import card_out, client_out, detail_out

router = APIRouter(prefix="/api", tags=["public"])
enquiry_limiter = RateLimiter(limit=5, window_s=600)


def _published_projects(db: Session) -> list[Project]:
    return list(
        db.scalars(
            select(Project)
            .where(Project.published.is_(True))
            .options(selectinload(Project.images))
            .order_by(Project.sort_order, Project.id)
        ).unique()
    )


def _etag_json(request: Request, payload: dict) -> Response:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    etag = '"' + hashlib.md5(body).hexdigest() + '"'  # nosec - cache validator only
    headers = {"ETag": etag, "Cache-Control": "no-cache"}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return Response(body, media_type="application/json", headers=headers)


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/bootstrap")
def bootstrap(request: Request, db: Session = Depends(get_db)):
    """One request gives the public site everything it needs for first paint."""
    offices = [OfficeOut.model_validate(o) for o in db.scalars(select(Office).order_by(Office.country))]
    site_images = {
        s.slot: SiteImageOut(slot=s.slot, alt_en=s.alt_en, alt_ar=s.alt_ar, image=image_out(s.image))
        for s in db.scalars(select(SiteImage))
    }
    clients = [
        client_out(c)
        for c in db.scalars(select(Client).where(Client.published.is_(True)).order_by(Client.sort_order, Client.id))
    ]
    data = BootstrapOut(
        offices=offices,
        site_images=site_images,
        clients=clients,
        projects=[card_out(p) for p in _published_projects(db)],
    )
    return _etag_json(request, data.model_dump(mode="json"))


@router.get("/projects/{slug}", response_model=ProjectDetailOut)
def project_detail(slug: str, db: Session = Depends(get_db)):
    p = db.scalar(
        select(Project)
        .where(Project.slug == slug, Project.published.is_(True))
        .options(selectinload(Project.images))
    )
    if not p:
        raise HTTPException(404, "Project not found")
    others = [x for x in _published_projects(db) if x.id != p.id]
    same_country = [x for x in others if x.country == p.country or x.type == p.type]
    related = (same_country + [x for x in others if x not in same_country])[:3]
    return detail_out(p, related)


@router.post("/enquiries", status_code=201)
def create_enquiry(data: EnquiryIn, request: Request, db: Session = Depends(get_db)):
    if data.website:  # honeypot hit: pretend success, store nothing
        return {"ok": True}
    enquiry_limiter.check(client_ip(request))
    db.add(
        Enquiry(
            name=data.name,
            phone=data.phone,
            email=data.email,
            country=data.country,
            service=data.service,
            project_type=data.project_type,
            area_m2=data.area_m2,
            message=data.message,
            contact_method=data.contact_method,
            lang=data.lang,
        )
    )
    db.commit()
    return {"ok": True}
