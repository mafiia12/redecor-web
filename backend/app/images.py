import hashlib
import io
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image as PILImage
from PIL import ImageOps, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import settings
from .models import Client, Image, Project, ProjectImage, SiteImage

PILImage.MAX_IMAGE_PIXELS = 80_000_000  # decompression-bomb guard
TARGET_WIDTHS = (480, 960, 1600, 2400)
ALLOWED = {"JPEG", "PNG", "WEBP"}


def image_dir(key: str) -> Path:
    return settings.upload_dir / key


def process_upload(db: Session, file: UploadFile, max_width: int = 2400) -> Image:
    """Validate, auto-rotate, strip metadata and write responsive WebP variants."""
    raw = file.file.read(settings.max_upload_bytes + 1)
    return process_bytes(db, raw, max_width)


def sha256_of(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def probe(raw: bytes) -> tuple[int, int]:
    """Real format + orientation-corrected size, without decoding the whole image twice. Raises HTTPException."""
    try:
        im = PILImage.open(io.BytesIO(raw))
        if im.format not in ALLOWED:
            raise HTTPException(415, "Use a JPEG, PNG or WebP image.")
        w, h = im.size
        if (im.getexif() or {}).get(0x0112) in (5, 6, 7, 8):  # rotated 90/270 degrees by EXIF orientation
            w, h = h, w
        return w, h
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, PILImage.DecompressionBombError):
        raise HTTPException(400, "The file is not a valid image.") from None


def quality_problems(w: int, h: int, cover: bool = False) -> list[str]:
    """Reasons a project photo is below the publishing standard (empty list = fine)."""
    problems = []
    need = settings.image_min_cover_long_edge if cover else settings.image_min_long_edge
    if max(w, h) < need:
        problems.append(f"{'cover ' if cover else ''}image too small: long edge {max(w, h)} px, minimum {need} px")
    ratio = w / h
    if ratio > settings.image_aspect_max:
        problems.append(f"too wide (panorama) {ratio:.2f}:1, maximum {settings.image_aspect_max}:1")
    if ratio < settings.image_aspect_min:
        problems.append(f"too tall {ratio:.2f}:1, minimum {settings.image_aspect_min}:1")
    return problems


def process_bytes(db: Session, raw: bytes, max_width: int = 2400) -> Image:
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(413, "Image is larger than 15 MB.")
    try:
        probe = PILImage.open(io.BytesIO(raw))
        if probe.format not in ALLOWED:
            raise HTTPException(415, "Use a JPEG, PNG or WebP image.")
        img = ImageOps.exif_transpose(PILImage.open(io.BytesIO(raw)))
        img.load()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, PILImage.DecompressionBombError):
        raise HTTPException(400, "The file is not a valid image.") from None

    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    img = img.convert("RGBA" if has_alpha else "RGB")
    w, h = img.size
    if w < 16 or h < 16:
        raise HTTPException(400, "Image is too small.")

    r, g, b = img.convert("RGB").resize((1, 1), PILImage.Resampling.BOX).getpixel((0, 0))
    color = f"#{r:02X}{g:02X}{b:02X}"
    cap = min(w, max_width)
    widths = sorted({x for x in TARGET_WIDTHS if x < cap} | {cap})

    key = uuid.uuid4().hex
    folder = image_dir(key)
    folder.mkdir(parents=True, exist_ok=True)
    try:
        for tw in widths:
            variant = img if tw == w else img.resize((tw, round(h * tw / w)), PILImage.Resampling.LANCZOS)
            variant.info.pop("exif", None)  # never carry EXIF (GPS, camera, owner) into public files
            variant.save(folder / f"{tw}.webp", "WEBP", quality=82, method=4, exif=b"", xmp=b"")
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(400, "Could not process the image.") from None

    rec = Image(key=key, width=cap, height=round(h * cap / w), widths=",".join(map(str, widths)), color=color,
                sha256=sha256_of(raw))
    db.add(rec)
    db.flush()
    return rec


def delete_if_orphan(db: Session, image_id: int | None) -> None:
    """Remove the image row and files when nothing references it any more."""
    if image_id is None:
        return
    used = (
        db.scalar(select(func.count()).select_from(ProjectImage).where(ProjectImage.image_id == image_id))
        or db.scalar(select(func.count()).select_from(Client).where(Client.logo_image_id == image_id))
        or db.scalar(select(func.count()).select_from(SiteImage).where(SiteImage.image_id == image_id))
        or db.scalar(select(func.count()).select_from(Project).where(Project.logo_image_id == image_id))
    )
    if used:
        return
    rec = db.get(Image, image_id)
    if rec:
        shutil.rmtree(image_dir(rec.key), ignore_errors=True)
        db.delete(rec)
