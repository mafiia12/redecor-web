"""Batch 2, phase A: launch-runbook items (health details, noindex on non-primary hosts, redirects, first-run admin)."""

import json

import pytest

from app import main as app_main
from app.config import settings


def test_health_details_need_admin_or_token(client, monkeypatch):
    assert client.get("/api/health/ready").json() == {"ok": True}
    monkeypatch.setattr(settings, "health_token", "monitor-token-123")
    assert client.get("/api/health/ready", headers={"X-Health-Token": "wrong"}).json() == {"ok": True}
    assert "database" in client.get("/api/health/ready", headers={"X-Health-Token": "monitor-token-123"}).json()


def test_noindex_header_on_non_primary_host(client, monkeypatch):
    monkeypatch.setattr(settings, "site_domain", "new.redecorgroup.com")
    monkeypatch.setattr(settings, "primary_domain", "redecorgroup.com")
    assert client.get("/api/health").headers["x-robots-tag"] == "noindex, nofollow"
    monkeypatch.setattr(settings, "site_domain", "redecorgroup.com")
    assert "x-robots-tag" not in client.get("/api/health").headers


def test_redirect_map_is_config_driven(client, tmp_path, monkeypatch):
    f = tmp_path / "redirects.json"
    f.write_text(json.dumps({"/old-page.html": "/about", "/portfolio/": "/projects"}))
    monkeypatch.setattr(settings, "redirects_file", str(f))
    app_main.load_redirects()
    try:
        r = client.get("/old-page.html", follow_redirects=False)
        assert r.status_code == 301 and r.headers["location"] == "/about"
        assert client.get("/portfolio", follow_redirects=False).headers["location"] == "/projects"
        f.write_text(json.dumps({"no-slash": "/x"}))
        with pytest.raises(RuntimeError):
            app_main.load_redirects()
    finally:
        monkeypatch.setattr(settings, "redirects_file", str(tmp_path / "missing.json"))
        app_main.load_redirects()
    assert app_main.REDIRECTS == {}  # empty by default


def test_production_requires_admin_password_only_on_first_run(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setenv("SECRET_KEY", "k" * 48)
    monkeypatch.setattr(settings, "site_url", "https://redecorgroup.com")
    monkeypatch.setattr(settings, "seed_demo", False)
    monkeypatch.setattr(settings, "admin_password", "")
    app_main.check_production()  # no password needed once an admin exists (checked against the DB at startup)
    monkeypatch.setattr(settings, "enforce_approvals", False)
    with pytest.raises(RuntimeError, match="ENFORCE_APPROVALS"):
        app_main.check_production()


def _start(tmp_path, **env):
    import os
    import subprocess
    import sys
    from pathlib import Path

    base = {
        "APP_ENV": "production", "SECRET_KEY": "k" * 48, "SITE_URL": "https://redecorgroup.com",
        "DATABASE_URL": f"sqlite:///{tmp_path / 'p.db'}", "UPLOAD_DIR": str(tmp_path / "up"),
        "ATTACHMENTS_DIR": str(tmp_path / "att"), "FRONTEND_DIST": str(tmp_path / "nodist"),
        "ADMIN_EMAIL": "", "ADMIN_PASSWORD": "", "SEED_DEMO": "0", "NOTIFY_RETRY_SECONDS": "0",
    }
    code = "from fastapi.testclient import TestClient\nfrom app.main import app\nwith TestClient(app) as c: print(c.get('/api/health').status_code)"
    return subprocess.run([sys.executable, "-c", code], env=os.environ | base | env, cwd=Path(__file__).parents[1],
                          capture_output=True, text=True)


def test_first_run_needs_admin_password_later_runs_do_not(tmp_path):
    r = _start(tmp_path)
    assert r.returncode != 0 and "No admin account exists yet" in r.stderr
    r = _start(tmp_path, ADMIN_EMAIL="owner@example.com", ADMIN_PASSWORD="First-start-pass-2026")
    assert r.returncode == 0, r.stderr
    r = _start(tmp_path)  # admin exists now: no password needed
    assert r.returncode == 0 and r.stdout.strip() == "200", r.stderr
