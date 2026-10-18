import asyncio
import os
import logging
import uuid
from contextlib import asynccontextmanager
from xml.sax.saxutils import escape

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
import time
from pathlib import Path

from sqlalchemy import func, select, text

from . import models  # noqa: F401  (register tables)
from .config import settings
from .db import Base, SessionLocal, engine, ensure_columns
from . import seo
from .models import Enquiry, Project
from .routers import admin, admin_system, public
from .alerts import alert
from .notify import retry_pending
from .security import password_problems
from .seed import seed
from .visibility import public_projects

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("redecor")


def check_production() -> None:
    """Refuse to start a production instance with unsafe settings (fail fast, before serving anyone)."""
    if not settings.is_production:
        return
    problems = []
    configured_key = os.getenv("SECRET_KEY", "")  # not the random fallback generated for development
    if len(configured_key) < 32 or "change-me" in configured_key:
        problems.append("SECRET_KEY must be a random string of at least 32 characters")
    if settings.seed_demo:
        problems.append("SEED_DEMO must be 0")
    if settings.allow_test_content:
        problems.append("ALLOW_TEST_CONTENT must be 0")
    if not settings.site_url.startswith("https://"):
        problems.append("SITE_URL must be the public https:// address")
    if settings.admin_password and password_problems(settings.admin_password, settings.admin_email):
        problems.append("ADMIN_PASSWORD does not meet the password policy (12+ characters, letters and numbers/symbols)")
    if problems:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))
    if not settings.smtp_configured:
        log.warning("SMTP is not configured: enquiries are stored but no e-mail notification is sent.")


async def _retry_loop() -> None:
    while True:
        await asyncio.sleep(settings.notify_retry_seconds)
        try:
            await asyncio.to_thread(retry_pending)
        except Exception:  # noqa: BLE001
            log.exception("Notification retry loop failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    check_production()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    (settings.upload_dir / "docs").mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)
    added = ensure_columns()
    if added:
        log.info("Database migrated, columns added: %s", ", ".join(added))
    with SessionLocal() as db:
        seed(db)
    task = asyncio.create_task(_retry_loop()) if settings.notify_retry_seconds > 0 else None
    if task:
        asyncio.get_running_loop().run_in_executor(None, retry_pending)  # pick up anything left from before a restart
    yield
    if task:
        task.cancel()


_docs = not settings.is_production
app = FastAPI(
    title="Redecor Group API",
    docs_url="/api/docs" if _docs else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if _docs else None,
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    # Drop the echoed input: it can be raw bytes (a wrong content type) that would crash JSON encoding.
    return JSONResponse({"detail": [{"loc": e.get("loc"), "msg": e.get("msg")} for e in exc.errors()]}, status_code=422)


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    rid = getattr(request.state, "request_id", "-")
    log.error("Unhandled error %s on %s %s", rid, request.method, request.url.path, exc_info=exc)
    alert("server-error", f"{type(exc).__name__} on {request.method} {request.url.path} (request {rid})")
    return JSONResponse({"detail": "Internal server error", "request_id": rid}, status_code=500)


if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
app.add_middleware(GZipMiddleware, minimum_size=800)

# Request body ceilings (checked from Content-Length before the body is read).
_BIG = 120 * 1024 * 1024  # several photos in one upload
_MEDIUM = 30 * 1024 * 1024  # one logo / slot image / PDF
_SMALL = 256 * 1024  # JSON


def _body_limit(path: str) -> int:
    if path.endswith("/images"):
        return _BIG
    if path.endswith("/logo") or "/site-images/" in path or "/documents/" in path:
        return _MEDIUM
    return _SMALL


CSP = (
    "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; "
    "font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; "
    "object-src 'none'"
)


@app.middleware("http")
async def guard(request: Request, call_next):
    request.state.request_id = uuid.uuid4().hex[:12]
    if request.method in ("POST", "PUT", "PATCH"):
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > _body_limit(request.url.path):
            return JSONResponse({"detail": "Request body too large"}, status_code=413)
    resp = await call_next(request)
    h = resp.headers
    h.setdefault("X-Content-Type-Options", "nosniff")
    h.setdefault("X-Frame-Options", "DENY")
    h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    h.setdefault("Content-Security-Policy", CSP)
    if settings.is_production:
        h.setdefault("Strict-Transport-Security", "max-age=15552000")
    if resp.status_code >= 500:
        log.error("HTTP %s %s %s (request %s)", resp.status_code, request.method, request.url.path, request.state.request_id)
    return resp


class ImmutableStatic(StaticFiles):
    """Uploaded variants never change in place (new upload = new key), so cache them for a year."""

    async def get_response(self, path, scope):
        resp = await super().get_response(path, scope)
        if resp.status_code == 200:
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return resp


app.include_router(public.router)
app.include_router(admin.router)
app.include_router(admin_system.router)


@app.get("/robots.txt", include_in_schema=False)
def robots():
    return PlainTextResponse(f"User-agent: *\nDisallow: /admin\nSitemap: {settings.site_url}/sitemap.xml\n")


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    base = settings.site_url
    paths = ["", "/projects", "/about", "/contact", "/services/contracting", "/services/fitout", "/services/supply", "/services/project-management"]
    with SessionLocal() as db:
        slugs = db.scalars(select(Project.slug).where(public_projects()).order_by(Project.sort_order, Project.id)).all()
    paths += [f"/projects/{s}" for s in slugs]
    urls = []
    for p in paths:
        alt = "/ar" + p if p else "/ar"
        urls.append(
            f"<url><loc>{escape(base + (p or '/'))}</loc>"
            f'<xhtml:link rel="alternate" hreflang="ar" href="{escape(base + alt)}"/></url>'
        )
        urls.append(f"<url><loc>{escape(base + alt)}</loc></url>")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'
        + "".join(urls)
        + "</urlset>"
    )
    return Response(xml, media_type="application/xml")


@app.api_route("/api/health/ready", methods=["GET", "HEAD"], include_in_schema=False)
def ready():
    """Deep check for uptime monitors: database, upload storage, notification backlog, backup age."""
    checks: dict[str, object] = {}
    ok = True
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            checks["failed_notifications"] = db.scalar(
                select(func.count()).select_from(Enquiry).where(Enquiry.notify_status.in_(("failed", "not_configured")))
            )
        checks["database"] = "ok"
    except Exception as e:  # noqa: BLE001
        ok, checks["database"] = False, type(e).__name__
    probe = settings.upload_dir / ".write-test"
    try:
        probe.write_text("ok")
        probe.unlink()
        checks["uploads"] = "ok"
    except OSError as e:
        ok, checks["uploads"] = False, type(e).__name__
    checks["smtp_configured"] = settings.smtp_configured
    if settings.backup_dir:
        latest = max(Path(settings.backup_dir).glob("redecor-backup-*.zip"), default=None, key=lambda f: f.stat().st_mtime)
        checks["last_backup_hours"] = round((time.time() - latest.stat().st_mtime) / 3600, 1) if latest else None
    return JSONResponse({"ok": ok, **checks}, status_code=200 if ok else 503)


@app.get("/api/{rest:path}", include_in_schema=False)
def api_not_found(rest: str):
    return JSONResponse({"detail": "Not found"}, status_code=404)


settings.upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", ImmutableStatic(directory=settings.upload_dir), name="media")

# Production: serve the built React app (single deployable). In dev, Vite serves it and proxies /api and /media.
# index.html is re-read whenever the build changes (no restart needed after `npm run build`).
_dist = settings.frontend_dist
app.mount("/assets", ImmutableStatic(directory=_dist / "assets", check_dir=False), name="assets")
_template: dict[str, object] = {"mtime": None, "html": ""}


def index_template() -> str | None:
    f = _dist / "index.html"
    try:
        mtime = f.stat().st_mtime
    except OSError:
        return None
    if _template["mtime"] != mtime:
        _template.update(mtime=mtime, html=f.read_text(encoding="utf-8"))
    return str(_template["html"])


@app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
def spa(path: str):
    if path.startswith(("api/", "media/", "assets/")):
        raise HTTPException(404)
    target = (_dist / path).resolve()
    if path and target.is_file() and _dist in target.parents:
        return FileResponse(target)
    template = index_template()
    if template is None:
        return PlainTextResponse("Frontend not built. Run: cd frontend && npm run build", status_code=503)
    headers = {"Cache-Control": "no-cache"}
    if path == "admin" or path.startswith("admin/"):
        html = template.replace("</head>", '<meta name="robots" content="noindex" /></head>', 1)
        return HTMLResponse(html, headers=headers)
    with SessionLocal() as db:
        head = seo.resolve(db, path)
    return HTMLResponse(seo.render(template, head), status_code=head.status, headers=headers)
