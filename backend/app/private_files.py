"""Private file store (enquiry attachments, approval evidence). Files live in ATTACHMENTS_DIR under random
names, outside every public/static folder; they are only ever returned by admin endpoints as downloads."""

import re
import uuid
from pathlib import Path

from fastapi.responses import FileResponse

from .config import settings

SAFE_TYPES = {
    "pdf": "application/pdf", "jpg": "image/jpeg", "png": "image/png", "zip": "application/zip",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel", "dwg": "application/octet-stream", "dxf": "application/octet-stream",
}


def _dir(area: str) -> Path:
    d = settings.attachments_dir / area
    d.mkdir(parents=True, exist_ok=True)
    return d


def save(area: str, raw: bytes) -> str:
    name = uuid.uuid4().hex
    (_dir(area) / name).write_bytes(raw)
    return name


def path_of(area: str, stored: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", stored):
        raise ValueError("bad stored name")
    return _dir(area) / stored


def clean_name(name: str) -> str:
    """Original file name kept only as display metadata (no paths, no control characters)."""
    base = Path((name or "file").replace("\\", "/")).name
    base = re.sub(r"[\x00-\x1f\x7f\"<>|:*?]", "_", base).strip(" .") or "file"
    return base[:200]


def download(area: str, stored: str, original: str, kind: str) -> FileResponse:
    ext = kind if kind in SAFE_TYPES else "bin"
    name = clean_name(original)
    if not name.lower().endswith(f".{ext}") and ext != "bin":
        name = f"{name}.{ext}"
    return FileResponse(
        path_of(area, stored),
        media_type=SAFE_TYPES.get(kind, "application/octet-stream"),
        filename=name,  # Starlette builds Content-Disposition: attachment; filename*=UTF-8''...
        content_disposition_type="attachment",
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
    )
