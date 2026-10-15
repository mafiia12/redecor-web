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
from .models import Client, Image, ProjectImage, SiteImage

PILImage.MAX_IMAGE_PIXELS = 80_000_000  # decompression-bomb guard
TARGET_WIDTHS = (480, 960, 1600, 2400)
ALLOWED = {"JPEG", "PNG", "WEBP"}


def image_dir(key: str) -> Path:
    return settings.upload_dir / key


def process_upload(db: Session, file: UploadFile, max_width: int = 2400) -> Image:
    """Validate, auto-rotate, strip metadata and write responsive WebP variants."""
    raw = file.file.read(settings.max_upload_bytes + 1)
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
        raise HTTPException(400, "The file is not a valid image.")

    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    img = img.convert("RGBA" if has_alpha else "RGB")
    w, h = img.size
    if w < 16 or h < 16:
        raise HTTPException(400, "Image is too small.")

    color = "#%02X%02X%02X" % img.convert("RGB").resize((1, 1), PILImage.Resampling.BOX).getpixel((0, 0))
    cap = min(w, max_width)
    widths = sorted({x for x in TARGET_WIDTHS if x < cap} | {cap})

    key = uuid.uuid4().hex
    folder = image_dir(key)
    folder.mkdir(parents=True, exist_ok=True)
    try:
        for tw in widths:
            variant = img if tw == w else img.resize((tw, round(h * tw / w)), PILImage.Resampling.LANCZOS)
            variant.save(folder / f"{tw}.webp", "WEBP", quality=82, method=4)
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(400, "Could not process the image.")

    rec = Image(key=key, width=cap, height=round(h * cap / w), widths=",".join(map(str, widths)), color=color)
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
    )
    if used:
        return
    rec = db.get(Image, image_id)
    if rec:
        shutil.rmtree(image_dir(rec.key), ignore_errors=True)
        db.delete(rec)
