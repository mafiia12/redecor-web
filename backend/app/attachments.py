"""Enquiry attachments: content-based type detection, ZIP inspection, optional ClamAV scan.

The file TYPE is decided from the bytes (magic numbers / container structure), never from the extension.
Allowed: PDF, DWG, DXF, XLSX, XLS, DOCX, JPG, PNG, ZIP. Rejected: everything else, macro-enabled Office
files, and ZIPs holding executables, nested archives, unsafe paths or "zip bomb" ratios.
"""

import io
import socket
import struct
import zipfile
from pathlib import PurePosixPath

from .config import settings

EXEC_EXT = {".exe", ".dll", ".com", ".bat", ".cmd", ".scr", ".msi", ".ps1", ".vbs", ".vbe", ".js", ".jse", ".wsf",
            ".hta", ".jar", ".sh", ".app", ".apk", ".lnk", ".cpl", ".pif", ".reg"}
MACRO_EXT = {".xlsm", ".xltm", ".xlam", ".docm", ".dotm", ".pptm", ".ppsm", ".potm"}
ARCHIVE_EXT = {".zip", ".rar", ".7z", ".gz", ".tgz", ".tar", ".bz2", ".xz", ".cab", ".iso"}
ZIP_MAX_ENTRIES = 500
ZIP_MAX_TOTAL = 300 * 1024 * 1024  # uncompressed
ZIP_MAX_RATIO = 100

LABELS = {"pdf": "PDF", "dwg": "DWG", "dxf": "DXF", "xlsx": "XLSX", "xls": "XLS", "docx": "DOCX",
          "jpg": "JPG", "png": "PNG", "zip": "ZIP"}


def _ole_kind(raw: bytes) -> tuple[str | None, str]:
    """Legacy Office (OLE2): accept Excel workbooks without VBA macros."""
    utf16 = lambda s: s.encode("utf-16-le")  # noqa: E731
    if utf16("_VBA_PROJECT") in raw or utf16("Macros") in raw or b"_VBA_PROJECT" in raw:
        return None, "macro-enabled Office file"
    if utf16("Workbook") in raw or utf16("Book") in raw:
        return "xls", ""
    return None, "unsupported Office file (only Excel .xls is accepted in the old format)"


def _zip_problem(z: zipfile.ZipFile) -> str:
    infos = z.infolist()
    if len(infos) > ZIP_MAX_ENTRIES:
        return f"zip has more than {ZIP_MAX_ENTRIES} entries"
    total = 0
    for i in infos:
        name = i.filename.replace("\\", "/")
        p = PurePosixPath(name)
        if name.startswith("/") or ".." in p.parts or (len(name) > 1 and name[1] == ":"):
            return f"unsafe path inside zip: {name[:80]}"
        ext = p.suffix.lower()
        if ext in EXEC_EXT:
            return f"executable inside zip: {p.name[:80]}"
        if ext in MACRO_EXT:
            return f"macro-enabled Office file inside zip: {p.name[:80]}"
        if ext in ARCHIVE_EXT:
            return f"nested archive inside zip: {p.name[:80]}"
        total += i.file_size
        if total > ZIP_MAX_TOTAL:
            return "zip expands to more than 300 MB"
        if i.compress_size and i.file_size / i.compress_size > ZIP_MAX_RATIO:
            return "suspicious compression ratio (zip bomb)"
    return ""


def inspect(raw: bytes, filename: str = "") -> tuple[str | None, str]:
    """Return (kind, problem). kind is one of LABELS when accepted; problem is a reason when rejected."""
    if PurePosixPath((filename or "").lower()).suffix in MACRO_EXT:
        return None, "macro-enabled Office files are not accepted"
    if not raw:
        return None, "empty file"
    if raw.startswith(b"%PDF-"):
        return "pdf", ""
    if raw[:3] == b"\xff\xd8\xff":
        return "jpg", ""
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", ""
    if raw[:4] == b"AC10" and raw[4:6].isdigit():
        return "dwg", ""
    if raw.startswith(b"AutoCAD Binary DXF"):
        return "dxf", ""
    head = raw[:200].lstrip().replace(b"\r\n", b"\n")
    if head.startswith(b"0\nSECTION") or head.startswith(b"999\n"):
        return "dxf", ""
    if raw.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return _ole_kind(raw)
    if raw[:4] in (b"PK\x03\x04", b"PK\x05\x06"):
        try:
            z = zipfile.ZipFile(io.BytesIO(raw))  # reads the central directory only, nothing is extracted
        except zipfile.BadZipFile:
            return None, "damaged zip file"
        names = set(z.namelist())
        if "[Content_Types].xml" in names:  # Office Open XML
            ct = z.read("[Content_Types].xml").decode("utf-8", "replace").lower()
            if any(n.lower().endswith("vbaproject.bin") for n in names) or "macroenabled" in ct:
                return None, "macro-enabled Office file"
            if any(n.startswith("xl/") for n in names):
                return "xlsx", ""
            if any(n.startswith("word/") for n in names):
                return "docx", ""
            return None, "unsupported Office file (only XLSX and DOCX)"
        problem = _zip_problem(z)
        return (None, problem) if problem else ("zip", "")
    return None, "file type not allowed (PDF, DWG, DXF, XLSX, XLS, DOCX, JPG, PNG or ZIP)"


def scan(raw: bytes) -> tuple[str, str]:
    """ClamAV INSTREAM scan. Returns (status, detail): clean | infected | error | quarantine (scanning off)."""
    if not settings.virus_scan_enabled:
        return "quarantine", "not scanned (virus scanning is off)"
    try:
        with socket.create_connection((settings.clamav_host, settings.clamav_port), timeout=30) as s:
            s.sendall(b"zINSTREAM\0")
            for i in range(0, len(raw), 1 << 16):
                chunk = raw[i : i + (1 << 16)]
                s.sendall(struct.pack("!L", len(chunk)) + chunk)
            s.sendall(struct.pack("!L", 0))
            reply = s.recv(4096).decode("utf-8", "replace").strip("\0\n ")
    except OSError as e:
        return "error", f"scanner unavailable ({type(e).__name__})"
    if reply.endswith("OK"):
        return "clean", "ClamAV: no threat found"
    if "FOUND" in reply:
        return "infected", reply.split(":", 1)[-1].strip()[:180]
    return "error", reply[:180]
