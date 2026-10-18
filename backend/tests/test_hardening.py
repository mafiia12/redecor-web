"""Publication rules, enquiries + notifications, roles, auth hardening, SEO head, migrations, analytics, documents."""

import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from app import main as app_main
from app import notify
from app.config import settings
from app.db import SessionLocal
from app.models import Enquiry
from app.routers import admin as admin_router

from .conftest import make_png

GOOD = dict(name="Mona Adel", phone="+20 100 222 3333", email="mona@example.com", country="eg", service="fitout", consent=True)


def _login(client, email, password):
    r = client.post("/api/admin/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _project(client, auth, **kw):
    body = dict(title_en="Villa Zamalek", country="eg", type="residential", published=True) | kw
    r = client.post("/api/admin/projects", headers=auth, json=body)
    assert r.status_code == 201, r.text
    return r.json()


# ---------- every admin endpoint is protected ----------
def test_every_admin_endpoint_requires_auth(client):
    checked = 0
    from app.routers import admin_system

    for route in [*admin_router.router.routes, *admin_system.router.routes]:
        path = getattr(route, "path", "")
        if not path.startswith("/api/admin") or path == "/api/admin/login":
            continue
        url = re.sub(r"\{[^}]+\}", "1", path)
        for method in route.methods - {"HEAD", "OPTIONS"}:
            r = client.request(method, url)
            assert r.status_code == 401, f"{method} {path} -> {r.status_code}"
            checked += 1
    assert checked > 30


# ---------- publication rules ----------
def test_drafts_test_and_placeholder_projects_stay_private(client, auth):
    live = _project(client, auth, title_en="Mall Fit-out Cairo")
    draft = _project(client, auth, title_en="Draft Office", published=False)
    test = _project(client, auth, title_en="Sample", slug="test-project-z")
    slugs = {p["slug"] for p in client.get("/api/bootstrap").json()["projects"]}
    assert live["slug"] in slugs and draft["slug"] not in slugs and test["slug"] not in slugs
    assert client.get(f"/api/projects/{draft['slug']}").status_code == 404
    assert client.get(f"/api/projects/{test['slug']}").status_code == 404
    assert client.get(f"/api/projects/{live['slug']}").status_code == 200
    assert not test["is_public"] and live["is_public"]
    # unfinished text cannot be published (a draft can still be saved)
    r = client.post("/api/admin/projects", headers=auth, json=dict(title_en="Hotel", summary_en="[Summary]", country="eg", type="hospitality"))
    assert r.status_code == 422
    assert _project(client, auth, title_en="Hotel", summary_en="[Summary]", published=False)["slug"]
    sitemap = client.get("/sitemap.xml").text
    assert live["slug"] in sitemap and draft["slug"] not in sitemap and "test-project-z" not in sitemap


def test_text_only_project_is_valid_and_has_prev_next(client, auth):
    a = _project(client, auth, title_en="Alpha Offices", sort_order=-20, summary_en="Offices.")
    b = _project(client, auth, title_en="Beta Clinic", sort_order=-10)
    d = client.get(f"/api/projects/{a['slug']}").json()
    assert d["gallery"] == [] and d["cover"] is None
    assert d["next"]["slug"] == b["slug"]
    assert client.get(f"/api/projects/{b['slug']}").json()["prev"]["slug"] == a["slug"]


def test_clients_need_approval_and_a_logo(client, auth):
    c = client.post("/api/admin/clients", headers=auth, json={"name": "Approved Co"}).json()
    assert c["published"] is False  # new clients start unpublished
    names = lambda: {x["name"] for x in client.get("/api/bootstrap").json()["clients"]}  # noqa: E731
    client.put(f"/api/admin/clients/{c['id']}", headers=auth, json={"name": "Approved Co", "published": True})
    assert "Approved Co" not in names()  # no logo yet
    client.post(f"/api/admin/clients/{c['id']}/logo", headers=auth, files={"file": ("l.png", make_png(), "image/png")})
    assert "Approved Co" in names()


# ---------- enquiries ----------
def _count_enquiries():
    with SessionLocal() as db:
        return db.query(Enquiry).count()


def test_enquiry_bot_timing_and_duplicates(client):
    before = _count_enquiries()
    assert client.post("/api/enquiries", json=GOOD | {"elapsed_ms": 300}).status_code == 201
    assert _count_enquiries() == before  # too fast: silently dropped
    r1 = client.post("/api/enquiries", json=GOOD | {"elapsed_ms": 9000, "message": "Kitchen and living room"})
    r2 = client.post("/api/enquiries", json=GOOD | {"elapsed_ms": 9500, "message": "Kitchen and living room"})
    assert r1.status_code == r2.status_code == 201
    assert r2.json().get("duplicate") is True
    assert _count_enquiries() == before + 1
    with SessionLocal() as db:
        e = db.query(Enquiry).order_by(Enquiry.id.desc()).first()
        assert e.notify_status == "not_configured"  # stored safely even without SMTP


@pytest.fixture()
def smtp(monkeypatch):
    sent = []
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_password", "s3cret-pass")
    monkeypatch.setattr(settings, "mail_from", "web@example.com")
    monkeypatch.setattr(settings, "notify_to", ["sales@example.com"])
    state = {"fail": False}

    def fake_send(msg):
        if state["fail"]:
            raise ConnectionRefusedError("connection refused using s3cret-pass")
        sent.append(msg)

    monkeypatch.setattr(notify, "send", fake_send)
    return sent, state


def test_notifications_sent_once_failures_kept_and_retried(client, auth, smtp):
    sent, state = smtp
    client.post("/api/enquiries", json=GOOD | {"name": "Omar Notify", "elapsed_ms": 5000})
    assert len(sent) == 1 and "Omar Notify" in sent[0]["Subject"] and sent[0]["Reply-To"] == GOOD["email"]
    with SessionLocal() as db:
        e = db.query(Enquiry).filter_by(name="Omar Notify").one()
        assert e.notify_status == "sent" and e.notified_at
        eid = e.id
    assert notify.deliver(eid) == "sent" and len(sent) == 1  # never twice
    assert client.post(f"/api/admin/enquiries/{eid}/notify", headers=auth).status_code == 409

    state["fail"] = True
    client.post("/api/enquiries", json=GOOD | {"name": "Laila Fail", "elapsed_ms": 5000})
    with SessionLocal() as db:
        e = db.query(Enquiry).filter_by(name="Laila Fail").one()
        assert e.notify_status == "failed" and e.notify_attempts == 1
        assert "s3cret-pass" not in e.notify_error  # credentials never stored
        fid = e.id
    state["fail"] = False
    assert notify.retry_pending() >= 1
    with SessionLocal() as db:
        assert db.get(Enquiry, fid).notify_status == "sent"
    listed = client.get("/api/admin/enquiries", headers=auth).json()
    assert any(x["id"] == fid and x["notify_status"] == "sent" for x in listed)


# ---------- auth hardening ----------
def test_roles_are_enforced_on_the_server(client, auth):
    for email, role in (("ed@test.com", "editor"), ("view@test.com", "viewer")):
        r = client.post("/api/admin/users", headers=auth, json={"email": email, "role": role, "password": "Strong-pass-2026"})
        assert r.status_code in (201, 409)
    ed = _login(client, "ed@test.com", "Strong-pass-2026")
    vw = _login(client, "view@test.com", "Strong-pass-2026")
    assert client.get("/api/admin/projects", headers=vw).status_code == 200
    assert client.post("/api/admin/projects", headers=vw, json={"title_en": "X", "country": "eg", "type": "office"}).status_code == 403
    assert client.get("/api/admin/enquiries", headers=vw).status_code == 403
    assert client.get("/api/admin/enquiries", headers=ed).status_code == 200
    assert client.get("/api/admin/users", headers=ed).status_code == 403
    assert client.put("/api/admin/offices/eg", headers=ed, json={}).status_code == 403
    weak = client.post("/api/admin/users", headers=auth, json={"email": "w@test.com", "role": "editor", "password": "short"})
    assert weak.status_code == 422
    # changing a role signs that user out
    vid = next(u["id"] for u in client.get("/api/admin/users", headers=auth).json() if u["email"] == "view@test.com")
    client.patch(f"/api/admin/users/{vid}", headers=auth, json={"role": "editor"})
    assert client.get("/api/admin/projects", headers=vw).status_code == 401
    # the last admin cannot be removed or demoted
    me = next(u for u in client.get("/api/admin/users", headers=auth).json() if u["email"] == "admin@test.com")
    assert client.patch(f"/api/admin/users/{me['id']}", headers=auth, json={"role": "viewer"}).status_code == 409
    assert client.delete(f"/api/admin/users/{me['id']}", headers=auth).status_code == 409


def test_password_change_revokes_old_sessions(client):
    client.post("/api/admin/users", headers=_login(client, "admin@test.com", "correct-horse-battery"),
                json={"email": "pw@test.com", "role": "editor", "password": "First-pass-2026"})
    old = _login(client, "pw@test.com", "First-pass-2026")
    bad = client.post("/api/admin/me/password", headers=old, json={"current_password": "nope", "new_password": "Second-pass-2026"})
    assert bad.status_code == 400
    weak = client.post("/api/admin/me/password", headers=old, json={"current_password": "First-pass-2026", "new_password": "abc"})
    assert weak.status_code == 422
    r = client.post("/api/admin/me/password", headers=old, json={"current_password": "First-pass-2026", "new_password": "Second-pass-2026"})
    assert r.status_code == 200
    assert client.get("/api/admin/me", headers=old).status_code == 401
    assert client.get("/api/admin/me", headers={"Authorization": f"Bearer {r.json()['token']}"}).status_code == 200


def test_tampered_or_expired_tokens_are_rejected(client):
    import jwt as pyjwt

    forged = pyjwt.encode({"sub": "admin@test.com", "iat": 1, "exp": 4102444800, "ver": 0}, "wrong-key-wrong-key-wrong-key-123", algorithm="HS256")
    assert client.get("/api/admin/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401
    expired = pyjwt.encode({"sub": "admin@test.com", "iat": 1, "exp": 2, "ver": 0}, settings.secret_key, algorithm="HS256")
    assert client.get("/api/admin/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    no_exp = pyjwt.encode({"sub": "admin@test.com", "iat": 1, "ver": 0}, settings.secret_key, algorithm="HS256")
    assert client.get("/api/admin/me", headers={"Authorization": f"Bearer {no_exp}"}).status_code == 401


def test_login_is_limited_per_account(client):
    for i in range(10):  # as if from 10 different IPs
        admin_router.login_limiter.reset()
        client.post("/api/admin/login", json={"email": "victim@test.com", "password": f"x{i}"})
    admin_router.login_limiter.reset()  # a fresh IP does not help: the account itself is now throttled
    r = client.post("/api/admin/login", json={"email": "victim@test.com", "password": "y"})
    assert r.status_code == 429


def test_body_limit_and_security_headers(client):
    r = client.post("/api/enquiries", content=b"{}", headers={"Content-Type": "application/json", "Content-Length": str(10 * 1024 * 1024)})
    assert r.status_code == 413
    h = client.get("/api/health").headers
    assert "default-src 'self'" in h["content-security-policy"] and h["x-frame-options"] == "DENY"


def test_production_guard(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setenv("SECRET_KEY", "")  # unset: the random development fallback must not count
    monkeypatch.setattr(settings, "site_url", "http://x")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        app_main.check_production()
    monkeypatch.setenv("SECRET_KEY", "k" * 48)
    monkeypatch.setattr(settings, "site_url", "https://redecorgroup.com")
    monkeypatch.setattr(settings, "seed_demo", False)
    monkeypatch.setattr(settings, "admin_password", "correct-horse-battery")
    monkeypatch.setattr(settings, "enforce_approvals", True)
    app_main.check_production()  # passes


# ---------- server-side head / status ----------
@pytest.fixture()
def dist(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text(
        '<!doctype html><html lang="en" dir="ltr"><head><title>x</title>'
        '<meta name="description" content="d" /><meta property="og:image" content="/og-default.png" /></head>'
        '<body><div id="root"></div></body></html>'
    )
    monkeypatch.setattr(app_main, "_dist", tmp_path)
    app_main._template["mtime"] = None
    return tmp_path


def test_seo_head_status_and_fresh_index(client, auth, dist):
    p = _project(client, auth, title_en="Nile Penthouse", title_ar="بنتهاوس النيل", summary_en="A penthouse on the Nile.")
    r = client.get(f"/projects/{p['slug']}")
    assert r.status_code == 200
    assert "<title>Nile Penthouse | RE DECOR &amp; MORE</title>" in r.text
    assert f'rel="canonical" href="{settings.site_url}/projects/{p["slug"]}"' in r.text
    assert 'hreflang="ar"' in r.text and "A penthouse on the Nile." in r.text
    ar = client.get(f"/ar/projects/{p['slug']}")
    assert 'lang="ar" dir="rtl"' in ar.text and "بنتهاوس النيل" in ar.text
    assert client.get("/projects/does-not-exist").status_code == 404
    assert client.get("/nope").status_code == 404 and "noindex" in client.get("/nope").text
    assert "noindex" in client.get("/admin/projects").text
    home = client.get("/").text
    assert '"@type": "Organization"' in home and "Redecor Group" in home
    # a new build is served without a restart
    (dist / "index.html").write_text((dist / "index.html").read_text().replace("<body>", "<body data-build='2'>"))
    os.utime(dist / "index.html", (9e9, 9e9))
    assert "data-build='2'" in client.get("/about").text


# ---------- migrations ----------
def _migrate(db, code):
    env = os.environ | {"DATABASE_URL": f"sqlite:///{db}"}
    return subprocess.run([sys.executable, "-c", "import app.models\nfrom app import migrations\n" + code],
                          env=env, cwd=Path(__file__).parents[1], capture_output=True, text=True, check=True).stdout


def test_forward_migration_adds_columns_and_backs_up(tmp_path):
    """An old first-release database (no schema_migrations table) is upgraded in place, keeping its rows."""
    db = tmp_path / "old.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR(255), password_hash VARCHAR(255), created_at DATETIME)")
    con.execute("INSERT INTO users (email, password_hash) VALUES ('keep@me.com', 'x')")
    con.commit()
    con.close()
    out = _migrate(db, "print(','.join(migrations.upgrade()))")
    assert "0001_baseline" in out and "0005_import_log" in out
    con = sqlite3.connect(db)
    assert con.execute("SELECT email, role, token_version FROM users").fetchall() == [("keep@me.com", "admin", 0)]
    assert list(tmp_path.glob("old.db.pre-migrate-*.bak"))  # rollback copy made before altering


def test_migrations_up_down_up_keep_data(tmp_path):
    db = tmp_path / "copy.db"
    _migrate(db, "migrations.upgrade()")
    con = sqlite3.connect(db)
    con.execute("INSERT INTO projects (slug, title_en, title_ar, summary_en, summary_ar, city_en, city_ar, country, type, "
                "scope_en, scope_ar, is_render, featured, published, sort_order, created_at, updated_at) VALUES "
                "('test-project-1','Test Project 1','','','','','','eg','office','','',0,1,0,0,'2026-01-01','2026-01-01')")
    con.commit()
    con.close()
    cols = lambda: {r[1] for r in sqlite3.connect(db).execute("PRAGMA table_info(project_images)")}  # noqa: E731
    tables = lambda: {r[0] for r in sqlite3.connect(db).execute("SELECT name FROM sqlite_master WHERE type='table'")}  # noqa: E731
    assert {"kind", "focal_x"} <= cols() and {"approvals", "enquiry_events", "import_log"} <= tables()
    out = _migrate(db, "print(','.join(migrations.downgrade(steps=4)))")
    assert out.strip() == "0005_import_log,0004_crm_attachments,0003_approvals,0002_media_quality"
    assert "kind" not in cols() and "approvals" not in tables() and "enquiry_events" not in tables()
    assert list(tmp_path.glob("copy.db.pre-downgrade-*.bak"))
    _migrate(db, "migrations.upgrade()")
    assert {"kind", "focal_x"} <= cols() and "approvals" in tables()
    rows = sqlite3.connect(db).execute("SELECT slug FROM projects").fetchall()
    assert rows == [("test-project-1",)]  # data survived up -> down -> up
    with pytest.raises(subprocess.CalledProcessError):
        _migrate(db, "migrations.downgrade(steps=99)")  # the baseline is never reverted


# ---------- analytics, documents, testimonials, preview, order ----------
def test_events_are_anonymous_counters(client, auth):
    for _ in range(3):
        assert client.post("/api/events", json={"name": "whatsapp_click", "path": "/projects/x?utm=1", "lang": "ar"}).status_code == 204
    assert client.post("/api/events", json={"name": "made_up", "path": "/"}).status_code == 422
    client.post("/api/events", json={"name": "project_view", "path": "/<script>"})
    data = client.get("/api/admin/analytics", headers=auth).json()
    assert data["totals"]["whatsapp_click"] >= 3
    assert all("<" not in p["path"] for p in data["top_projects"])


def test_profile_document_and_testimonials_publish_rules(client, auth):
    assert client.put("/api/admin/documents/company-profile", headers=auth, files={"file": ("x.pdf", b"not a pdf", "application/pdf")}).status_code == 415
    up = client.put("/api/admin/documents/company-profile", headers=auth, files={"file": ("Profile.pdf", b"%PDF-1.4 test", "application/pdf")})
    assert up.status_code == 200 and up.json()["published"] is False
    assert client.get("/api/bootstrap").json()["documents"] == {}
    client.patch("/api/admin/documents/company-profile?published=true", headers=auth)
    doc = client.get("/api/bootstrap").json()["documents"]["company-profile"]
    assert client.get(doc["url"]).content.startswith(b"%PDF-")

    t = dict(author="Client Name", quote_en="Great work.", published=True)
    assert client.post("/api/admin/testimonials", headers=auth, json=t).status_code == 422  # no approval yet
    client.post("/api/admin/testimonials", headers=auth, json=t | {"approved": True, "approval_note": "E-mail 2026-10-01"})
    assert [x["author"] for x in client.get("/api/bootstrap").json()["testimonials"]] == ["Client Name"]


def test_draft_preview_and_reorder(client, auth):
    a = _project(client, auth, title_en="Order A", published=False)
    b = _project(client, auth, title_en="Order B", published=False)
    pv = client.get(f"/api/admin/projects/{a['id']}/preview", headers=auth)
    assert pv.status_code == 200 and pv.json()["title_en"] == "Order A"
    assert client.put("/api/admin/projects-order", headers=auth, json={"ids": [b["id"], a["id"]]}).status_code == 204
    got = {p["id"]: p["sort_order"] for p in client.get("/api/admin/projects", headers=auth).json()}
    assert got[b["id"]] < got[a["id"]]
    assert "Photos" in client.get(f"/api/admin/projects/{a['id']}", headers=auth).json()["missing"]


def test_ready_health(client, auth):
    r = client.get("/api/health/ready")
    assert r.status_code == 200 and r.json() == {"ok": True}  # public: no internal details
    d = client.get("/api/health/ready", headers=auth).json()
    assert d["database"] == "ok" and d["uploads"] == "ok"


def test_head_requests_for_uptime_monitors(client):
    assert client.head("/api/health").status_code == 200
    assert client.head("/api/health/ready").status_code == 200


def test_real_smtp_round_trip(client, monkeypatch):
    """Talks to a real (local) SMTP server: the message must actually be accepted before 'sent' is recorded."""
    aiosmtpd = pytest.importorskip("aiosmtpd.controller")
    received = []

    class Handler:
        async def handle_DATA(self, server, session, envelope):  # noqa: N802
            received.append(envelope)
            return "250 OK"

    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    ctl = aiosmtpd.Controller(Handler(), hostname="127.0.0.1", port=port)
    ctl.start()
    try:
        monkeypatch.setattr(settings, "smtp_host", "127.0.0.1")
        monkeypatch.setattr(settings, "smtp_port", port)
        monkeypatch.setattr(settings, "smtp_security", "none")
        monkeypatch.setattr(settings, "smtp_user", "")
        monkeypatch.setattr(settings, "mail_from", "web@example.com")
        monkeypatch.setattr(settings, "notify_to", ["sales@example.com"])
        client.post("/api/enquiries", json=GOOD | {"name": "Real Smtp", "elapsed_ms": 4000})
        assert len(received) == 1 and received[0].rcpt_tos == ["sales@example.com"]
        assert b"Real Smtp" in received[0].content
        with SessionLocal() as db:
            assert db.query(Enquiry).filter_by(name="Real Smtp").one().notify_status == "sent"
    finally:
        ctl.stop()

    # server gone: the enquiry is still saved and marked failed for retry
    client.post("/api/enquiries", json=GOOD | {"name": "Smtp Down", "elapsed_ms": 4000})
    with SessionLocal() as db:
        e = db.query(Enquiry).filter_by(name="Smtp Down").one()
        assert e.notify_status == "failed" and e.notify_error
