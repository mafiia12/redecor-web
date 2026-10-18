import re
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, object_session, selectinload

from ..config import settings
from ..db import get_db
from ..images import delete_if_orphan, probe, process_bytes, process_upload, quality_problems, sha256_of
from ..models import Approval, AuditLog, Client, Office, Project, ProjectImage, SiteImage, User
from ..schemas import (
    ClientAdminOut,
    ClientIn,
    LoginIn,
    OfficeIn,
    OfficeOut,
    OrderIn,
    PasswordChangeIn,
    ProjectAdminOut,
    ProjectDetailOut,
    ProjectImageAdminOut,
    ProjectImagePatch,
    ProjectIn,
    SiteImageAltIn,
    image_out,
)
from ..security import (
    RateLimiter,
    admin_only,
    client_ip,
    create_token,
    current_user,
    editor,
    hash_password,
    password_problems,
    verify_password,
    viewer,
)
from ..serializers import cover_of, project_image_out
from ..slots import SLOT_KEYS, SLOTS
from ..visibility import REQUIRED_APPROVAL, TEST_SLUG_PREFIX, is_placeholder
from .public import project_payload

router = APIRouter(prefix="/api/admin", tags=["admin"])
login_limiter = RateLimiter(limit=8, window_s=300)  # per IP
account_limiter = RateLimiter(limit=10, window_s=900)  # per e-mail, against distributed guessing

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
    email = data.email.strip().lower()
    login_limiter.check(client_ip(request))
    account_limiter.check(email)
    user = db.scalar(select(User).where(User.email == email))
    ok = verify_password(data.password, user.password_hash if user else _DUMMY)
    if not user or not ok:
        raise HTTPException(401, "Incorrect email or password")
    return {"token": create_token(user), "email": user.email, "role": user.role}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"email": user.email, "role": user.role}


@router.post("/me/password")
def change_password(data: PasswordChangeIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Change your own password. All other sessions are signed out; a fresh token is returned."""
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    problems = password_problems(data.new_password, user.email)
    if problems:
        raise HTTPException(422, " ".join(problems))
    user.password_hash = hash_password(data.new_password)
    user.token_version = (user.token_version or 0) + 1
    audit(db, user, "password", "user", user.id)
    db.commit()
    return {"token": create_token(user), "email": user.email, "role": user.role}


# ---------- projects ----------
# What makes a project page feel complete. Photos are recommended but never required (text-only pages are valid).
_CHECKS = [
    ("title_ar", "Arabic title"),
    ("city_en", "City"),
    ("summary_en", "Summary (English)"),
    ("summary_ar", "Summary (Arabic)"),
    ("year", "Year"),
    ("scope_en", "Scope"),
    ("details_en", "Details (facts)"),
    ("images", "Photos"),
]


def completeness(p: Project) -> tuple[int, list[str]]:
    missing = [label for f, label in _CHECKS if not (p.images if f == "images" else getattr(p, f))]
    return round(100 * (len(_CHECKS) - len(missing)) / len(_CHECKS)), missing


def _approval(db: Session, subject_type: str, sid: int) -> str:
    a = db.scalar(select(Approval).where(Approval.subject_type == subject_type, Approval.subject_id == sid,
                                        Approval.approval_type == REQUIRED_APPROVAL[subject_type])
                  .order_by(Approval.id.desc()).limit(1))
    return a.status if a else "none"


def _block_reasons(p: Project) -> list[str]:
    """Why the public cannot see this project right now (empty list = it is visible)."""
    reasons = []
    if not p.published:
        reasons.append("Draft (not published)")
    if is_placeholder(p.title_en):
        reasons.append("Title still contains [placeholder] text")
    if not settings.allow_test_content and p.slug.startswith(TEST_SLUG_PREFIX):
        reasons.append("Test project (test-project-*)")
    db = object_session(p)
    if settings.enforce_approvals and db is not None and _approval(db, "project", p.id) != "approved":
        reasons.append("No approved 'client permission to publish' on record (Approvals)")
    return reasons


def _is_public(p: Project) -> bool:
    return not _block_reasons(p)


def _project_out(p: Project) -> ProjectAdminOut:
    cover = cover_of(p)
    score, missing = completeness(p)
    return ProjectAdminOut(
        **{f: getattr(p, f) for f in ProjectIn.model_fields},
        id=p.id,
        logo=image_out(p.logo),
        cover=image_out(cover.image) if cover else None,
        images=[project_image_out(i, admin=True) for i in p.images],
        completeness=score,
        missing=missing,
        is_public=not (reasons := _block_reasons(p)),
        block_reasons=reasons,
        images_without_kind=sum(i.kind not in ("render", "executed") for i in p.images),
    )


def _publish_guard(data: ProjectIn) -> None:
    """A published page may be text-only, but it must not show unfinished "[placeholder]" text."""
    if not data.published:
        return
    fields = ("title_en", "title_ar", "summary_en", "summary_ar", "city_en", "city_ar", "scope_en", "scope_ar",
              "tagline_en", "tagline_ar", "details_en", "details_ar", "client_name")
    bad = [f for f in fields if is_placeholder(getattr(data, f))]
    if bad:
        raise HTTPException(422, f"Replace the [placeholder] text before publishing ({', '.join(bad)}), or save as draft.")


def _get_project(db: Session, pid: int) -> Project:
    p = db.scalar(select(Project).where(Project.id == pid).options(selectinload(Project.images)))
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@router.get("/projects", response_model=list[ProjectAdminOut])
def list_projects(db: Session = Depends(get_db), _: User = Depends(viewer)):
    rows = db.scalars(select(Project).options(selectinload(Project.images)).order_by(Project.sort_order, Project.id))
    return [_project_out(p) for p in rows.unique()]


@router.get("/projects/{pid}", response_model=ProjectAdminOut)
def get_project(pid: int, db: Session = Depends(get_db), _: User = Depends(viewer)):
    return _project_out(_get_project(db, pid))


@router.post("/projects", response_model=ProjectAdminOut, status_code=201)
def create_project(data: ProjectIn, db: Session = Depends(get_db), user: User = Depends(editor)):
    _publish_guard(data)
    values = data.model_dump()
    values["slug"] = unique_slug(db, slugify(data.slug or data.title_en))
    p = Project(**values)
    db.add(p)
    db.flush()
    audit(db, user, "create", "project", p.id)
    db.commit()
    return _project_out(_get_project(db, p.id))


@router.put("/projects/{pid}", response_model=ProjectAdminOut)
def update_project(pid: int, data: ProjectIn, db: Session = Depends(get_db), user: User = Depends(editor)):
    p = _get_project(db, pid)
    _publish_guard(data)
    if data.published and any(i.kind not in ("render", "executed") for i in p.images):
        raise HTTPException(422, "Every photo needs a label (Render or Executed) before the project can be published.")
    values = data.model_dump()
    values["slug"] = unique_slug(db, slugify(data.slug or p.slug), exclude_id=p.id)
    for k, v in values.items():
        setattr(p, k, v)
    audit(db, user, "update", "project", p.id)
    db.commit()
    return _project_out(_get_project(db, pid))


@router.put("/projects-order", status_code=204)
def reorder_projects(data: OrderIn, db: Session = Depends(get_db), user: User = Depends(editor)):
    """Save the display order in one request (the list order becomes sort_order 10, 20, 30...)."""
    rows = {p.id: p for p in db.scalars(select(Project).where(Project.id.in_(data.ids)))}
    for n, pid in enumerate(data.ids, start=1):
        if pid in rows:
            rows[pid].sort_order = n * 10
    audit(db, user, "reorder", "project", len(rows))
    db.commit()


@router.get("/projects/{pid}/preview", response_model=ProjectDetailOut)
def preview_project(pid: int, db: Session = Depends(get_db), _: User = Depends(viewer)):
    """The project page exactly as the public would see it, including drafts (admin only)."""
    p = _get_project(db, pid)
    return project_payload(db, p)


@router.delete("/projects/{pid}", status_code=204)
def delete_project(pid: int, db: Session = Depends(get_db), user: User = Depends(editor)):
    p = _get_project(db, pid)
    image_ids = [i.image_id for i in p.images]
    db.delete(p)
    db.flush()
    for iid in image_ids:
        delete_if_orphan(db, iid)
    close_approvals(db, "project", pid, user)
    audit(db, user, "delete", "project", pid)
    db.commit()


def close_approvals(db: Session, subject_type: str, sid: int, user: User) -> None:
    """A deleted item's approvals must not pass to a new item that later gets the same id (SQLite reuses ids):
    append a 'revoked' row for every approval type on record. Nothing is edited or removed."""
    types = db.scalars(select(Approval.approval_type).where(Approval.subject_type == subject_type,
                                                            Approval.subject_id == sid).distinct()).all()
    for t in types:
        db.add(Approval(subject_type=subject_type, subject_id=sid, approval_type=t, status="revoked",
                        evidence_note=f"{subject_type} deleted", recorded_by=user.email))


def add_project_image(db: Session, p: Project, raw: bytes, user: User, *, kind: str | None = None,
                      order: int | None = None, cover: bool | None = None, alt_en: str = "", alt_ar: str = "",
                      override: bool = False) -> ProjectImage | None:
    """The single entry point for project photos (admin upload, bulk upload). Quality-checked and de-duplicated.
    Returns None when the same file is already attached to the project."""
    digest = sha256_of(raw)
    if any(i.image.sha256 == digest for i in p.images):
        return None
    w, h = probe(raw)
    is_cover = (not p.images) if cover is None else cover
    problems = quality_problems(w, h, cover=is_cover)
    if problems and not override:
        raise HTTPException(422, "Image rejected: " + "; ".join(problems) + ". Tick “accept below standard” to keep it anyway.")
    img = process_bytes(db, raw)
    if is_cover:
        for other in p.images:
            other.is_cover = False
    pi = ProjectImage(
        project_id=p.id, image_id=img.id, is_cover=is_cover,
        sort_order=order if order is not None else max([i.sort_order for i in p.images], default=-1) + 1,
        kind=kind, is_render=kind == "render", alt_en=alt_en, alt_ar=alt_ar,
    )
    if problems:
        pi.quality_warnings = "; ".join(problems)[:300]
        pi.quality_override_by, pi.quality_override_at = user.email, datetime.now(timezone.utc)
    db.add(pi)
    db.flush()
    p.images.append(pi)
    return pi


@router.post("/projects/{pid}/images", response_model=list[ProjectImageAdminOut], status_code=201)
def upload_project_images(
    pid: int,
    files: list[UploadFile] = File(...),
    kind: Literal["render", "executed"] | None = Form(None),
    override_quality: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(editor),
):
    if len(files) > 20:
        raise HTTPException(400, "Upload at most 20 images at a time.")
    p = _get_project(db, pid)
    created: list[ProjectImage] = []
    for f in files:
        raw = f.file.read(settings.max_upload_bytes + 1)
        pi = add_project_image(db, p, raw, user, kind=kind, override=override_quality)
        if pi:
            created.append(pi)
    if not created and files:
        raise HTTPException(409, "These images are already attached to this project (duplicates skipped).")
    db.flush()
    audit(db, user, "upload", "project_image", pid)
    db.commit()
    return [project_image_out(db.get(ProjectImage, c.id), admin=True) for c in created]


@router.post("/projects/{pid}/logo", response_model=ProjectAdminOut)
def upload_project_logo(
    pid: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(editor)
):
    """Client / brand logo shown on a banner at the top of the project page."""
    p = _get_project(db, pid)
    old = p.logo_image_id
    img = process_upload(db, file, max_width=960)
    p.logo_image_id = img.id
    db.flush()
    delete_if_orphan(db, old)
    audit(db, user, "upload", "project_logo", pid)
    db.commit()
    db.expire_all()
    return _project_out(_get_project(db, pid))


@router.delete("/projects/{pid}/logo", status_code=204)
def delete_project_logo(pid: int, db: Session = Depends(get_db), user: User = Depends(editor)):
    p = _get_project(db, pid)
    old, p.logo_image_id = p.logo_image_id, None
    db.flush()
    delete_if_orphan(db, old)
    audit(db, user, "delete", "project_logo", pid)
    db.commit()


@router.patch("/project-images/{iid}", response_model=ProjectImageAdminOut)
def patch_project_image(
    iid: int, data: ProjectImagePatch, db: Session = Depends(get_db), user: User = Depends(editor)
):
    pi = db.get(ProjectImage, iid)
    if not pi:
        raise HTTPException(404, "Image not found")
    changes = data.model_dump(exclude_unset=True)
    override = changes.pop("override_quality", False)
    if "kind" in changes:
        changes["is_render"] = changes["kind"] == "render"
    if changes.get("is_cover"):
        problems = quality_problems(pi.image.width, pi.image.height, cover=True)
        if problems and not (override or pi.quality_override_by):
            raise HTTPException(422, "Not suitable as cover: " + "; ".join(problems) + ". Tick “accept below standard” to use it anyway.")
        if problems:
            pi.quality_warnings = "; ".join(problems)[:300]
            pi.quality_override_by, pi.quality_override_at = user.email, datetime.now(timezone.utc)
    if changes.get("is_cover"):  # only one cover per project
        for other in db.scalars(select(ProjectImage).where(ProjectImage.project_id == pi.project_id)):
            other.is_cover = False
    for k, v in changes.items():
        setattr(pi, k, v)
    audit(db, user, "update", "project_image", iid)
    db.commit()
    return project_image_out(pi, admin=True)


@router.delete("/project-images/{iid}", status_code=204)
def delete_project_image(iid: int, db: Session = Depends(get_db), user: User = Depends(editor)):
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
    db = object_session(c)
    status = _approval(db, "client", c.id) if db is not None else "none"
    reasons = []
    if not c.published:
        reasons.append("Not published")
    if c.logo_image_id is None:
        reasons.append("No logo uploaded")
    if settings.enforce_approvals and status != "approved":
        reasons.append("No approved 'logo usage permission' on record (Approvals)")
    return ClientAdminOut(
        id=c.id, name=c.name, url=c.url, published=c.published, sort_order=c.sort_order, logo=image_out(c.logo),
        approval_status=status, is_public=not reasons, block_reasons=reasons,
    )


@router.get("/clients", response_model=list[ClientAdminOut])
def list_clients(db: Session = Depends(get_db), _: User = Depends(viewer)):
    return [_client_out(c) for c in db.scalars(select(Client).order_by(Client.sort_order, Client.id))]


@router.post("/clients", response_model=ClientAdminOut, status_code=201)
def create_client(data: ClientIn, db: Session = Depends(get_db), user: User = Depends(editor)):
    c = Client(**data.model_dump())
    db.add(c)
    db.flush()
    audit(db, user, "create", "client", c.id)
    db.commit()
    return _client_out(c)


@router.put("/clients/{cid}", response_model=ClientAdminOut)
def update_client(cid: int, data: ClientIn, db: Session = Depends(get_db), user: User = Depends(editor)):
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
    cid: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(editor)
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
def delete_client(cid: int, db: Session = Depends(get_db), user: User = Depends(editor)):
    c = db.get(Client, cid)
    if not c:
        raise HTTPException(404, "Client not found")
    old = c.logo_image_id
    db.delete(c)
    db.flush()
    delete_if_orphan(db, old)
    close_approvals(db, "client", cid, user)
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
def list_site_images(db: Session = Depends(get_db), _: User = Depends(viewer)):
    return [_slot_out(db, k, label) for k, label in SLOTS]


@router.put("/site-images/{slot}")
def upload_site_image(
    slot: str, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(editor)
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
    slot: str, data: SiteImageAltIn, db: Session = Depends(get_db), user: User = Depends(editor)
):
    s = db.get(SiteImage, slot)
    if not s:
        raise HTTPException(404, "Upload an image first")
    s.alt_en, s.alt_ar = data.alt_en, data.alt_ar
    audit(db, user, "update", "site_image", slot)
    db.commit()
    return _slot_out(db, slot, dict(SLOTS)[slot])


@router.delete("/site-images/{slot}", status_code=204)
def delete_site_image(slot: str, db: Session = Depends(get_db), user: User = Depends(editor)):
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
def list_offices(db: Session = Depends(get_db), _: User = Depends(viewer)):
    return db.scalars(select(Office).order_by(Office.country)).all()


@router.put("/offices/{country}", response_model=OfficeOut)
def update_office(country: str, data: OfficeIn, db: Session = Depends(get_db), user: User = Depends(admin_only)):
    o = db.get(Office, country)
    if not o:
        raise HTTPException(404, "Office not found")
    for k, v in data.model_dump().items():
        setattr(o, k, v)
    audit(db, user, "update", "office", country)
    db.commit()
    return o


# ---------- enquiries: see admin_crm.py ----------
