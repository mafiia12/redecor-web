"""Batch 2, phase C1: project import from Excel / CSV / JSON manifest."""

import io
import json
import os
import subprocess
import sys
from pathlib import Path

from openpyxl import Workbook, load_workbook

from app.db import SessionLocal
from app.models import AuditLog, ImportLog, Project

TOOLS = Path(__file__).resolve().parents[2] / "tools"
AR_TITLE = "مشروع اختبار"  # Arabic test text, kept as escapes
AR_CITY = "القاهرة"
HEADER = "slug,title_en,title_ar,country,type,city_ar,year,is_render\n"


def csv_bytes(body: str, bom: bool) -> bytes:
    return (HEADER + body).encode("utf-8-sig" if bom else "utf-8")


def xlsx_bytes(rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Projects"
    ws.append(["slug", "title_en", "title_ar", "country", "type", "city_ar", "year"])
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def plan(client, auth, name, raw, **form):
    r = client.post("/api/admin/import/plan", headers=auth, files={"file": (name, raw)}, data=form)
    assert r.status_code == 200, r.text
    return r.json()


def apply(client, auth, name, raw, **form):
    r = client.post("/api/admin/import/apply", headers=auth, files={"file": (name, raw)}, data=form)
    assert r.status_code == 200, r.text
    return r.json()


def project(slug):
    with SessionLocal() as db:
        p = db.query(Project).filter_by(slug=slug).one_or_none()
        return None if p is None else {c: getattr(p, c) for c in ("title_en", "title_ar", "city_ar", "published", "year", "is_render")}


def test_template_has_columns_and_instructions(client, auth):
    r = client.get("/api/admin/import/template", headers=auth)
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    wb = load_workbook(io.BytesIO(r.content))
    assert wb.sheetnames == ["Projects", "Instructions"]
    header = [c.value for c in wb["Projects"][1]]
    assert header[:5] == ["slug", "title_en", "title_ar", "country", "type"] and "published" not in header
    assert wb["Projects"].max_row == 1  # no sample rows that could be imported by mistake
    assert any("drafts" in str(c.value) for row in wb["Instructions"].iter_rows() for c in row)


def test_dry_run_reports_cells_and_writes_nothing(client, auth):
    raw = csv_bytes("test-imp-1,Test Project 1,,eg,office,,2024,no\n"
                    ",,,xx,castle,,abc,maybe\n"
                    "test-imp-1,Test Project 1 again,,eg,office,,,\n", bom=False)
    before = project("test-imp-1")
    out = plan(client, auth, "p.csv", raw)
    assert out["summary"] == {"create": 1, "update": 0, "skip": 0, "error": 2}
    bad = out["rows"][1]
    assert bad["row"] == 3 and bad["action"] == "error"
    joined = " | ".join(bad["errors"])
    for col in ("year:", "is_render:", "title_en:", "country:", "type:"):
        assert col in joined, joined
    assert "same project as row 2" in " ".join(out["rows"][2]["errors"])
    assert project("test-imp-1") == before is None


def test_apply_creates_unpublished_with_backup_and_audit(client, auth):
    raw = csv_bytes("test-imp-2,Test Project 2,,qa,retail,,2023,yes\n", bom=True)
    out = apply(client, auth, "p.csv", raw)
    assert out["summary"]["create"] == 1 and out["backup"].endswith(".bak")
    p = project("test-imp-2")
    assert p["published"] is False and p["is_render"] is True and p["year"] == 2023
    with SessionLocal() as db:
        log = db.query(ImportLog).filter_by(kind="projects").order_by(ImportLog.id.desc()).first()
        assert log.created == 1 and log.user_email == "admin@test.com" and Path(log.backup_file).stat().st_size > 0
        assert db.query(AuditLog).filter_by(action="import-create").count() >= 1
    # same file again: exists -> skip (no update without the explicit option)
    again = apply(client, auth, "p.csv", raw)
    assert again["summary"] == {"create": 0, "update": 0, "skip": 1, "error": 0}


def test_update_existing_only_with_option_and_only_filled_cells(client, auth):
    apply(client, auth, "a.csv", csv_bytes(f"test-imp-3,Test Project 3,{AR_TITLE},eg,office,{AR_CITY},2020,no\n", bom=False))
    change = csv_bytes("test-imp-3,Test Project 3 renamed,,eg,office,,2021,\n", bom=False)
    assert plan(client, auth, "b.csv", change)["summary"]["skip"] == 1
    assert project("test-imp-3")["title_en"] == "Test Project 3"
    out = apply(client, auth, "b.csv", change, update_existing="true")
    assert out["summary"]["update"] == 1
    p = project("test-imp-3")
    assert p["title_en"] == "Test Project 3 renamed" and p["year"] == 2021
    assert p["title_ar"] == AR_TITLE and p["city_ar"] == AR_CITY  # empty cells left the old values alone
    assert p["published"] is False


def test_arabic_round_trip_csv_with_and_without_bom_and_xlsx(client, auth):
    for i, bom in enumerate((True, False)):
        slug = f"test-imp-ar-{i}"
        apply(client, auth, "ar.csv", csv_bytes(f"{slug},Test Project AR,{AR_TITLE},eg,office,{AR_CITY},,\n", bom=bom))
        assert project(slug)["title_ar"] == AR_TITLE and project(slug)["city_ar"] == AR_CITY
    apply(client, auth, "ar.xlsx", xlsx_bytes([["test-imp-ar-x", "Test Project AR x", AR_TITLE, "eg", "office", AR_CITY, 2022]]))
    assert project("test-imp-ar-x")["title_ar"] == AR_TITLE and project("test-imp-ar-x")["year"] == 2022
    # and back out: the readiness export keeps Arabic intact in both formats
    csv_out = client.get("/api/admin/readiness?format=csv", headers=auth)
    assert csv_out.content.startswith(b"\xef\xbb\xbf") and AR_TITLE in csv_out.content.decode("utf-8-sig")
    x = load_workbook(io.BytesIO(client.get("/api/admin/readiness?format=xlsx", headers=auth).content))
    assert any(AR_TITLE == c.value for row in x.active.iter_rows() for c in row)


def test_non_utf8_csv_is_refused_with_advice(client, auth):
    raw = (HEADER + f"test-imp-cp,Test Project cp,{AR_TITLE},eg,office,,,\n").encode("cp1256")
    r = client.post("/api/admin/import/plan", headers=auth, files={"file": ("x.csv", raw)})
    assert r.status_code == 400 and "CSV UTF-8" in r.json()["detail"]


def test_manifest_json_is_accepted(client, auth):
    manifest = json.loads((TOOLS / "portfolio_manifest.json").read_text(encoding="utf-8"))
    out = plan(client, auth, "portfolio_manifest.json", json.dumps(manifest).encode())
    assert len(out["rows"]) == len(manifest) == 59
    assert out["summary"]["error"] == 0, [r for r in out["rows"] if r["errors"]][:3]
    assert project(manifest[0]["slug"]) is None  # dry-run only


def test_cli_dry_run_writes_nothing(client, auth, tmp_path):
    f = tmp_path / "p.csv"
    f.write_bytes(csv_bytes("test-imp-cli,Test Project CLI,,eg,office,,,\n", bom=True))
    env = {**os.environ, "PYTHONPATH": str(TOOLS.parent / "backend")}
    r = subprocess.run([sys.executable, str(TOOLS / "import_projects.py"), "--file", str(f)], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    assert "1 create" in r.stdout and "DRY-RUN" in r.stdout
    assert project("test-imp-cli") is None


def test_viewer_cannot_import(client, auth):
    r = client.post("/api/admin/users", headers=auth, json={"email": "viewer-imp@example.com", "password": "Viewer-pass-2026!", "role": "viewer"})
    assert r.status_code in (200, 201), r.text
    tok = client.post("/api/admin/login", json={"email": "viewer-imp@example.com", "password": "Viewer-pass-2026!"}).json()["token"]
    r = client.post("/api/admin/import/plan", headers={"Authorization": f"Bearer {tok}"}, files={"file": ("p.csv", csv_bytes("", bom=False))})
    assert r.status_code == 403
