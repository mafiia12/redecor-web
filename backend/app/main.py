import logging
from contextlib import asynccontextmanager
from xml.sax.saxutils import escape

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from . import models  # noqa: F401  (register tables)
from .config import settings
from .db import Base, SessionLocal, engine
from .models import Project
from .routers import admin, public
from .seed import seed

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    yield


app = FastAPI(title="Redecor Group API", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
app.add_middleware(GZipMiddleware, minimum_size=800)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
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


@app.get("/api/{rest:path}", include_in_schema=False)
def api_not_found(rest: str):
    return JSONResponse({"detail": "Not found"}, status_code=404)


@app.get("/robots.txt", include_in_schema=False)
def robots():
    return PlainTextResponse(f"User-agent: *\nDisallow: /admin\nSitemap: {settings.site_url}/sitemap.xml\n")


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    base = settings.site_url
    paths = ["", "/projects", "/about", "/contact", "/services/design", "/services/fitout", "/services/supply"]
    with SessionLocal() as db:
        slugs = db.scalars(select(Project.slug).where(Project.published.is_(True))).all()
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


settings.upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", ImmutableStatic(directory=settings.upload_dir), name="media")

# Production: serve the built React app (single deployable). In dev, Vite serves it and proxies /api and /media.
_dist = settings.frontend_dist
if (_dist / "index.html").exists():
    if (_dist / "assets").exists():
        app.mount("/assets", ImmutableStatic(directory=_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        target = (_dist / path).resolve()
        if path and target.is_file() and _dist in target.parents:
            return FileResponse(target)
        if path.startswith(("api/", "media/")):
            raise HTTPException(404)
        return FileResponse(_dist / "index.html", headers={"Cache-Control": "no-cache"})
