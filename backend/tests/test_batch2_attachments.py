"""Batch 2, phase C3: quote-form attachments (content checks, limits, private storage, admin download, virus scan)."""

import io
import json
import os
import socket
import subprocess
import sys
import threading
import zipfile
from pathlib import Path

import pytest
from openpyxl import Workbook

from app import attachments
from app.config import settings
from app.db import SessionLocal
from app.models import AuditLog, Enquiry, EnquiryAttachment
from app.notify import build_message

from .conftest import make_png

TOOLS = Path(__file__).resolve().parents[2] / "tools"
URL = "/api/enquiries/with-files"
_n = iter(range(10_000))


def form(name="Test Upload", **kw):
    """A valid enquiry; each call gets a unique message so the duplicate filter does not merge them."""
    body = dict(name=name, phone="+20 100 123 4567", email="t@example.com", country="eg", service="fitout", consent=True,
                elapsed_ms=5000, message=f"Test message {next(_n)}", lang="en") | kw
    return {"data": json.dumps(body)}


def zip_of(entries: dict[str, bytes], compression=zipfile.ZIP_DEFLATED) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression) as z:
        for n, b in entries.items():
            z.writestr(n, b)
    return buf.getvalue()


def xlsx() -> bytes:
    wb = Workbook()
    wb.active.append(["BOQ item", "Qty"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def docx(macro=False) -> bytes:
    ct = '<Types><Override ContentType="application/vnd.ms-word.document.macroEnabled.main+xml"/></Types>' if macro else "<Types/>"
    entries = {"[Content_Types].xml": ct.encode(), "word/document.xml": b"<w:document/>"}
    if macro:
        entries["word/vbaProject.bin"] = b"\0" * 10
    return zip_of(entries)


PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
OK_FILES = {
    "drawing.pdf": PDF,
    "photo.png": make_png(64, 48),
    "photo.jpg": b"\xff\xd8\xff\xe0" + b"\0" * 64,
    "plan.dwg": b"AC1032" + b"\0" * 64,
    "plan.dxf": b"  0\nSECTION\n  2\nHEADER\n  0\nENDSEC\n  0\nEOF\n",
    "boq.xlsx": xlsx(),
    "old.xls": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + "Workbook".encode("utf-16-le") + b"\0" * 64,
    "spec.docx": docx(),
    "bundle.zip": zip_of({"a.pdf": PDF, "b.png": make_png(32, 32)}),
}


@pytest.mark.parametrize("name", list(OK_FILES))
def test_allowed_types_are_detected_from_content(name):
    kind, problem = attachments.inspect(OK_FILES[name], name)
    assert kind == name.rsplit(".", 1)[1] and problem == ""


@pytest.mark.parametrize("name,raw,reason", [
    ("invoice.pdf", b"MZ\x90\x00" + b"\0" * 64, "not allowed"),  # an executable renamed to .pdf
    ("page.html", b"<html><script>alert(1)</script></html>", "not allowed"),
    ("budget.xlsm", xlsx(), "macro"),
    ("spec.docx", docx(macro=True), "macro"),
    ("old.xls", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + "Workbook".encode("utf-16-le") + "_VBA_PROJECT".encode("utf-16-le"), "macro"),
    ("tools.zip", zip_of({"setup.exe": b"MZ"}), "executable"),
    ("nested.zip", zip_of({"inner.zip": zip_of({"a.pdf": PDF})}), "nested archive"),
    ("evil.zip", zip_of({"../../etc/x.pdf": PDF}), "unsafe path"),
    ("bomb.zip", zip_of({"zeros.pdf": b"\0" * (20 * 1024 * 1024)}), "zip bomb"),
])
def test_dangerous_files_are_rejected(name, raw, reason):
    kind, problem = attachments.inspect(raw, name)
    assert kind is None and reason in problem


def test_quote_with_files_is_stored_privately_and_downloadable_by_admin_only(client, auth):
    files = [("files", ("Plan <v2>.pdf", PDF, "application/pdf")), ("files", ("boq.xlsx", OK_FILES["boq.xlsx"], "application/octet-stream"))]
    r = client.post(URL, data=form("Test Files OK"), files=files)
    assert r.status_code == 201, r.text
    with SessionLocal() as db:
        e = db.query(Enquiry).filter_by(name="Test Files OK").one()
        rows = list(e.attachments)
        eid = e.id
    assert [a.detected_type for a in rows] == ["pdf", "xlsx"]
    a = rows[0]
    assert a.original_name == "Plan _v2_.pdf" and len(a.stored_name) == 32 and "pdf" not in a.stored_name
    stored = settings.attachments_dir / "attachments" / a.stored_name
    assert stored.read_bytes() == PDF
    assert not any(p.name == a.stored_name for p in settings.upload_dir.rglob("*"))  # never in the public folder
    assert client.get(f"/media/{a.stored_name}").status_code == 404
    assert a.scan_status == "quarantine" and "not scanned" in a.scan_detail  # VIRUS_SCAN_ENABLED=0 in tests

    listed = next(x for x in client.get("/api/admin/enquiries", headers=auth).json() if x["id"] == eid)
    assert listed["attachment_count"] == 2
    d = client.get(f"/api/admin/enquiries/{eid}/attachments/{a.id}", headers=auth)
    assert d.status_code == 200 and d.content == PDF
    assert d.headers["content-disposition"].startswith("attachment;")
    assert d.headers["x-content-type-options"] == "nosniff" and d.headers["content-type"] == "application/pdf"
    assert "no-store" in d.headers["cache-control"]
    with SessionLocal() as db:
        assert db.query(AuditLog).filter_by(action="download", entity="enquiry_attachment", entity_id=str(a.id)).count() == 1
    assert client.get(f"/api/admin/enquiries/{eid}/attachments/{a.id}").status_code == 401
    assert client.get(f"/api/admin/enquiries/{eid + 999}/attachments/{a.id}", headers=auth).status_code == 404

    # the notification names the count and never carries the files
    with SessionLocal() as db:
        msg = build_message(db.get(Enquiry, eid))
    assert "Attachments: 2" in msg.get_content() and not any(p.get_filename() for p in msg.walk())


def test_bad_file_is_refused_and_nothing_is_stored(client):
    with SessionLocal() as db:
        before = db.query(Enquiry).count(), db.query(EnquiryAttachment).count()
    r = client.post(URL, data=form("Test Bad File"), files=[("files", ("x.pdf", b"MZ" + b"\0" * 10, "application/pdf"))])
    assert r.status_code == 422 and r.json()["detail"]["code"] == "file_type" and r.json()["detail"]["file"] == "x.pdf"
    with SessionLocal() as db:
        assert (db.query(Enquiry).count(), db.query(EnquiryAttachment).count()) == before


def test_limits_count_size_total_and_body(client, monkeypatch):
    four = [("files", (f"f{i}.pdf", PDF, "application/pdf")) for i in range(4)]
    r = client.post(URL, data=form(), files=four)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "too_many_files"
    monkeypatch.setattr(settings, "attach_max_file_mb", 1)
    big = PDF + b"\0" * (1024 * 1024)
    r = client.post(URL, data=form(), files=[("files", ("big.pdf", big, "application/pdf"))])
    assert r.status_code == 413 and r.json()["detail"]["code"] == "file_too_large"
    monkeypatch.setattr(settings, "attach_max_file_mb", 15)
    monkeypatch.setattr(settings, "attach_max_total_mb", 1)
    half = PDF + b"\0" * (600 * 1024)
    r = client.post(URL, data=form(), files=[("files", ("a.pdf", half, "application/pdf")), ("files", ("b.pdf", half + b"1", "application/pdf"))])
    assert r.status_code == 413 and r.json()["detail"]["code"] == "total_too_large"
    # the body ceiling refuses an oversized request before the app reads it (Caddy does the same in front)
    huge = PDF + b"\0" * (3 * 1024 * 1024)
    r = client.post(URL, data=form(), files=[("files", ("h.pdf", huge, "application/pdf"))])
    assert r.status_code == 413


def test_honeypot_with_files_stores_nothing(client):
    with SessionLocal() as db:
        before = db.query(EnquiryAttachment).count()
    r = client.post(URL, data=form("Test Bot", website="http://spam.example.com"), files=[("files", ("a.pdf", PDF, "application/pdf"))])
    assert r.status_code == 201
    with SessionLocal() as db:
        assert db.query(EnquiryAttachment).count() == before


class FakeClamd:
    """Minimal clamd INSTREAM responder."""

    def __init__(self, reply: bytes):
        self.reply = reply
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen()
        self.port = self.sock.getsockname()[1]
        threading.Thread(target=self.serve, daemon=True).start()

    def serve(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            with conn:
                data = b""
                while not data.endswith(b"\0\0\0\0"):
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    data += chunk
                conn.sendall(self.reply)


@pytest.mark.parametrize("reply,status", [(b"stream: OK\0", "clean"), (b"stream: Eicar-Signature FOUND\0", "infected")])
def test_virus_scan_results(client, auth, monkeypatch, reply, status):
    clam = FakeClamd(reply)
    monkeypatch.setattr(settings, "virus_scan_enabled", True)
    monkeypatch.setattr(settings, "clamav_host", "127.0.0.1")
    monkeypatch.setattr(settings, "clamav_port", clam.port)
    name = f"Test Scan {status}"
    assert client.post(URL, data=form(name), files=[("files", ("a.pdf", PDF, "application/pdf"))]).status_code == 201
    with SessionLocal() as db:
        e = db.query(Enquiry).filter_by(name=name).one()
        a = e.attachments[0]
        assert a.scan_status == status
        eid, aid = e.id, a.id
    code = client.get(f"/api/admin/enquiries/{eid}/attachments/{aid}", headers=auth).status_code
    assert code == (200 if status == "clean" else 409)
    clam.sock.close()


def test_scanner_down_never_loses_the_enquiry(client, monkeypatch):
    monkeypatch.setattr(settings, "virus_scan_enabled", True)
    monkeypatch.setattr(settings, "clamav_host", "127.0.0.1")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        monkeypatch.setattr(settings, "clamav_port", s.getsockname()[1])  # nothing listens here
    assert client.post(URL, data=form("Test Scanner Down"), files=[("files", ("a.pdf", PDF, "application/pdf"))]).status_code == 201
    with SessionLocal() as db:
        e = db.query(Enquiry).filter_by(name="Test Scanner Down").one()
        assert e.attachments[0].scan_status == "error"


def test_backup_includes_attachments(client, tmp_path):
    client.post(URL, data=form("Test Backup Files"), files=[("files", ("a.pdf", PDF, "application/pdf"))])
    env = {**os.environ, "PYTHONPATH": str(TOOLS.parent / "backend")}
    r = subprocess.run([sys.executable, str(TOOLS / "backup.py"), "--attachments", str(settings.attachments_dir),
                        "--uploads", str(settings.upload_dir), "--out-dir", str(tmp_path)], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr + r.stdout
    archive = next(tmp_path.glob("*.zip"))
    with zipfile.ZipFile(archive) as z:
        assert any(n.startswith("attachments/attachments/") for n in z.namelist())
