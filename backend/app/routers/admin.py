import re
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..images import delete_if_orphan, process_upload
from ..models import AuditLog, Client, Enquiry, Office, Project, ProjectImage, SiteImage, User
from ..schemas import (
    ClientAdminOut,
    ClientIn,
    EnquiryAdminOut,
    EnquiryStatusIn,
    LoginIn,
    OfficeIn,
    OfficeOut,
    ProjectAdminOut,
    ProjectImageOut,
    ProjectImagePatch,
    ProjectIn,
    SiteImageAltIn,
    image_out,
)
from ..security import RateLimiter, client_ip, create_token, current_user, verify_password
from ..serializers import cover_of, project_image_out
from ..slots import SLOT_KEYS, SLOTS

router = APIRouter(prefix="/api/admin", tags=["admin"])
login_limiter = RateLimiter(limit=8, window_s=300)

# A dummy hash so unknown emails cost the same time as wrong passwords.
_DUMMY = "scrypt$" + "00" * 16 + "$" + "00" * 32


def audit(db: Session, user: User, action: str, entity: str, entity_id: object = "") -> None:
    db.add(AuditLog(user_email=user.email, action=action, entity=entity, entity_id=str(entity_id)))


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:100] or "project"


def unique_slug(db: Session, base: str, exclude_id: int | None = None) -> str:
    slug, n = base, 2
    while True:
        existing = db.scalar(select(Project).where(Project.slug == slug))
        if not existing or existing.id == exclude_id:
            return slug
        slug, n = f"{base}-{n}", n + 1


# ---------- auth ----------
@router.post("/login")
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    login_limiter.check(client_ip(request))
    user = db.scalar(select(User).where(User.email == data.email.strip().lower()))
    ok = verify_password(data.password, user.password_hash if user else _DUMMY)
    if not user or not ok:
        raise HTTPException(401, "Incorrect email or password")
    return {"token": create_token(user.email), "email": user.email}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"email": user.email}


# ---------- projects ----------
def _project_out(p: Project) -> ProjectAdminOut:
    cover = cover_of(p)
    return ProjectAdminOut(
        **{f: getattr(p, f) for f in ProjectIn.model_fields},
        id=p.id,
        cover=image_out(cover.image) if cover else None,
        images=[project_image_out(i) for i in p.images],
    )


def _get_project(db: Session, pid: int) -> Project:
    p = db.scalar(select(Project).where(Project.id == pid).options(selectinload(Project.images)))
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@router.get("/projects", response_model=list[ProjectAdminOut])
def list_projects(db: Session = Depends(get_db), _: User = Depends(current_user)):
    rows = db.scalars(select(Project).options(selectinload(Project.images)).order_by(Project.sort_order, Project.id))
    return [_project_out(p) for p in rows.unique()]


@router.get("/projects/{pid}", response_model=ProjectAdminOut)
def get_project(pid: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    return _project_out(_get_project(db, pid))


@router.post("/projects", response_model=ProjectAdminOut, status_code=201)
def create_project(data: ProjectIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    values = data.model_dump()
    values["slug"] = unique_slug(db, slugify(data.slug or data.title_en))
    p = Project(**values)
    db.add(p)
    db.flush()
    audit(db, user, "create", "project", p.id)
    db.commit()
    return _project_out(_get_project(db, p.id))


@router.put("/projects/{pid}", response_model=ProjectAdminOut)
def update_project(pid: int, data: ProjectIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = _get_project(db, pid)
    values = data.model_dump()
    values["slug"] = unique_slug(db, slugify(data.slug or p.slug), exclude_id=p.id)
    for k, v in values.items():
        setattr(p, k, v)
    audit(db, user, "update", "project", p.id)
    db.commit()
    return _project_out(_get_project(db, pid))


@router.delete("/projects/{pid}", status_code=204)
def delete_project(pid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = _get_project(db, pid)
    image_ids = [i.image_id for i in p.images]
    db.delete(p)
    db.flush()
    for iid in image_ids:
        delete_if_orphan(db, iid)
    audit(db, user, "delete", "project", pid)
    db.commit()


@router.post("/projects/{pid}/images", response_model=list[ProjectImageOut], status_code=201)
def upload_project_images(
    pid: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if len(files) > 20:
        raise HTTPException(400, "Upload at most 20 images at a time.")
    p = _get_project(db, pid)
    next_order = max([i.sort_order for i in p.images], default=-1) + 1
    created: list[ProjectImage] = []
    for f in files:
        img = process_upload(db, f)
        pi = ProjectImage(
            project_id=p.id,
            image_id=img.id,
            is_cover=not p.images and not created,  # first image becomes the cover
            sort_order=next_order + len(created),
        )
        db.add(pi)
        created.append(pi)
    db.flush()
    audit(db, user, "upload", "project_image", pid)
    db.commit()
    return [project_image_out(db.get(ProjectImage, c.id)) for c in created]


@router.patch("/project-images/{iid}", response_model=ProjectImageOut)
def patch_project_image(
    iid: int, data: ProjectImagePatch, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    pi = db.get(ProjectImage, iid)
    if not pi:
        raise HTTPException(404, "Image not found")
    changes = data.model_dump(exclude_unset=True)
    if changes.get("is_cover"):  # only one cover per project
        for other in db.scalars(select(ProjectImage).where(ProjectImage.project_id == pi.project_id)):
            other.is_cover = False
    for k, v in changes.items():
        setattr(pi, k, v)
    audit(db, user, "update", "project_image", iid)
    db.commit()
    return project_image_out(pi)


@router.delete("/project-images/{iid}", status_code=204)
def delete_project_image(iid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    pi = db.get(ProjectImage, iid)
    if not pi:
        raise HTTPException(404, "Image not found")
    image_id, project_id, was_cover = pi.image_id, pi.project_id, pi.is_cover
    db.delete(pi)
    db.flush()
    delete_if_orphan(db, image_id)
    if was_cover:
        nxt = db.scalar(
            select(ProjectImage).where(ProjectImage.project_id == project_id).order_by(ProjectImage.sort_order)
        )
        if nxt:
            nxt.is_cover = True
    audit(db, user, "delete", "project_image", iid)
    db.commit()


# ---------- clients ----------
def _client_out(c: Client) -> ClientAdminOut:
    return ClientAdminOut(
        id=c.id, name=c.name, url=c.url, published=c.published, sort_order=c.sort_order, logo=image_out(c.logo)
    )


@router.get("/clients", response_model=list[ClientAdminOut])
def list_clients(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return [_client_out(c) for c in db.scalars(select(Client).order_by(Client.sort_order, Client.id))]


@router.post("/clients", response_model=ClientAdminOut, status_code=201)
def create_client(data: ClientIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = Client(**data.model_dump())
    db.add(c)
    db.flush()
    audit(db, user, "create", "client", c.id)
    db.commit()
    return _client_out(c)


@router.put("/clients/{cid}", response_model=ClientAdminOut)
def update_client(cid: int, data: ClientIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = db.get(Client, cid)
    if not c:
        raise HTTPException(404, "Client not found")
    for k, v in data.model_dump().items():
        setattr(c, k, v)
    audit(db, user, "update", "client", cid)
    db.commit()
    return _client_out(c)


@router.post("/clients/{cid}/logo", response_model=ClientAdminOut)
def upload_client_logo(
    cid: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)
):
    c = db.get(Client, cid)
    if not c:
        raise HTTPException(404, "Client not found")
    old = c.logo_image_id
    img = process_upload(db, file, max_width=960)
    c.logo_image_id = img.id
    db.flush()
    delete_if_orphan(db, old)
    audit(db, user, "upload", "client_logo", cid)
    db.commit()
    db.refresh(c)  # relationship was cached before the logo id changed
    return _client_out(c)


@router.delete("/clients/{cid}", status_code=204)
def delete_client(cid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = db.get(Client, cid)
    if not c:
        raise HTTPException(404, "Client not found")
    old = c.logo_image_id
    db.delete(c)
    db.flush()
    delete_if_orphan(db, old)
    audit(db, user, "delete", "client", cid)
    db.commit()


# ---------- site image slots ----------
def _slot_out(db: Session, slot: str, label: str) -> dict:
    s = db.get(SiteImage, slot)
    return {
        "slot": slot,
        "label": label,
        "alt_en": s.alt_en if s else "",
        "alt_ar": s.alt_ar if s else "",
        "image": image_out(s.image).model_dump() if s else None,
    }


@router.get("/site-images")
def list_site_images(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return [_slot_out(db, k, label) for k, label in SLOTS]


@router.put("/site-images/{slot}")
def upload_site_image(
    slot: str, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)
):
    if slot not in SLOT_KEYS:
        raise HTTPException(404, "Unknown image slot")
    img = process_upload(db, file)
    existing = db.get(SiteImage, slot)
    old = existing.image_id if existing else None
    if existing:
        existing.image_id = img.id
    else:
        db.add(SiteImage(slot=slot, image_id=img.id))
    db.flush()
    delete_if_orphan(db, old)
    audit(db, user, "upload", "site_image", slot)
    db.commit()
    db.expire_all()
    return _slot_out(db, slot, dict(SLOTS)[slot])


@router.patch("/site-images/{slot}")
def update_site_image_alt(
    slot: str, data: SiteImageAltIn, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    s = db.get(SiteImage, slot)
    if not s:
        raise HTTPException(404, "Upload an image first")
    s.alt_en, s.alt_ar = data.alt_en, data.alt_ar
    audit(db, user, "update", "site_image", slot)
    db.commit()
    return _slot_out(db, slot, dict(SLOTS)[slot])


@router.delete("/site-images/{slot}", status_code=204)
def delete_site_image(slot: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    s = db.get(SiteImage, slot)
    if not s:
        raise HTTPException(404, "No image in this slot")
    old = s.image_id
    db.delete(s)
    db.flush()
    delete_if_orphan(db, old)
    audit(db, user, "delete", "site_image", slot)
    db.commit()


# ---------- offices ----------
@router.get("/offices", response_model=list[OfficeOut])
def list_offices(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return db.scalars(select(Office).order_by(Office.country)).all()


@router.put("/offices/{country}", response_model=OfficeOut)
def update_office(country: str, data: OfficeIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    o = db.get(Office, country)
    if not o:
        raise HTTPException(404, "Office not found")
    for k, v in data.model_dump().items():
        setattr(o, k, v)
    audit(db, user, "update", "office", country)
    db.commit()
    return o


# ---------- enquiries ----------
def _enquiry_out(e: Enquiry) -> EnquiryAdminOut:
    return EnquiryAdminOut.model_validate(e)


@router.get("/enquiries", response_model=list[EnquiryAdminOut])
def list_enquiries(db: Session = Depends(get_db), _: User = Depends(current_user)):
    rows = db.scalars(select(Enquiry).order_by(Enquiry.created_at.desc()).limit(500))
    return [_enquiry_out(e) for e in rows]


@router.patch("/enquiries/{eid}", response_model=EnquiryAdminOut)
def set_enquiry_status(
    eid: int, data: EnquiryStatusIn, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    e = db.get(Enquiry, eid)
    if not e:
        raise HTTPException(404, "Enquiry not found")
    e.status = data.status
    audit(db, user, f"status:{data.status}", "enquiry", eid)
    db.commit()
    return _enquiry_out(e)
