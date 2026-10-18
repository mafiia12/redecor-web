#!/usr/bin/env python3
"""Pull the best image from each PDF page of a project and upload it through the admin API.

Usage (run on the machine that has the PDFs, with the backend running):
  pip install -r tools/requirements.txt
  python tools/import_portfolio.py --pdf-dir "D:\\Master Web (Redecor)" --dry-run          # preview only, no upload
  python tools/import_portfolio.py --pdf-dir "D:\\Master Web (Redecor)" --email you@x.com   # upload (prompts for password)
Projects are created as HIDDEN unless you pass --publish, so you can review them in /admin first.
"""
import argparse
import getpass
import hashlib
import io
import json
import os
import sys
from pathlib import Path

try:
    import pymupdf as fitz  # PyMuPDF >= 1.24.3
except ImportError:  # older releases
    import fitz
import requests
from PIL import Image

MIN_SIDE = 700  # ignore logos / icons smaller than this
MAX_W = 2400


def page_images(doc, page, seen: set[str], all_images: bool = False) -> list[Image.Image]:
    """Largest embedded picture on the page (or every large picture), else a render of the page."""
    found = []
    for info in page.get_images(full=True):
        xref = info[0]
        try:
            pix = fitz.Pixmap(doc, xref)
            if pix.n - pix.alpha > 3:  # CMYK etc.
                pix = fitz.Pixmap(fitz.csRGB, pix)
            if min(pix.width, pix.height) < MIN_SIDE:
                continue
            found.append((pix.width * pix.height, pix))
        except Exception:
            continue
    found.sort(key=lambda t: -t[0])
    imgs = []
    if found:
        for _, pix in (found if all_images else found[:1]):
            imgs.append(Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB"))
    else:
        zoom = 1800 / page.rect.width
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        if img.getextrema() != ((255, 255),) * 3:  # skip blank pages
            imgs.append(img)
    out = []
    for img in imgs:
        digest = hashlib.md5(img.resize((32, 32)).tobytes()).hexdigest()
        if digest in seen:  # same picture repeated on several pages
            continue
        seen.add(digest)
        if img.width > MAX_W:
            img = img.resize((MAX_W, round(img.height * MAX_W / img.width)), Image.LANCZOS)
        out.append(img)
    return out


def jpeg_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85, optimize=True)
    return buf.getvalue()


# The manifest uses logical names; real file names vary (spaces, "&", typos), so match on a keyword.
PDF_KEYWORDS = {  # any keyword matches (case-insensitive, letters and digits only)
    "Redecor_Fit-out_projects.pdf": ["fitout"],
    "OCEANS_BREEZE.pdf": ["ocean"],
    "Retail_Commerical_Portfolio.pdf": ["commer"],  # Commerical / Commercial
    "Resedintial__in_egypt_Portfolio.pdf": ["egypt"],
    "Resedintial_in_Gulf_Portfolio.pdf": ["gulf"],
    "Redecor_Portfolio_brief.pdf": ["breif", "brief"],
}


def find_pdf(pdf_dir: Path, logical: str) -> Path | None:
    keys = PDF_KEYWORDS.get(logical, [])
    for f in sorted(pdf_dir.rglob("*.pdf")):
        norm = "".join(ch for ch in f.name.lower() if ch.isalnum())
        if f.name == logical or (keys and any(k in norm for k in keys)):
            return f
    return None


def collect(project: dict, pdf_dir: Path, max_images: int):
    """Returns [(label, image, is_render)] across every source of the project."""
    sources = project.get("sources") or [{"pdf": project["pdf"], "pages": project["pages"]}]
    out = []
    seen: set[str] = set()
    for src in sources:
        path = find_pdf(pdf_dir, src["pdf"])
        if not path:
            found = ", ".join(f.name for f in sorted(pdf_dir.rglob("*.pdf"))) or "none"
            print(f"  ! no PDF matching {src['pdf']!r}. PDFs found in the folder: {found}")
            continue
        doc = fitz.open(path)
        first, last = src["pages"]
        for n in range(first, min(last, len(doc)) + 1):
            for k, img in enumerate(page_images(doc, doc[n - 1], seen, project.get("all_images", False))):
                out.append((f"{n}{'abcdefgh'[k] if k else ''}", img, bool(src.get("render")), ""))
    if len(out) > max_images:  # keep an even spread through the project
        step = len(out) / max_images
        out = [out[int(i * step)] for i in range(max_images)]
    return out


def load_folder(folder: Path, max_images: int):
    """Images from a folder (e.g. best renders pulled from the company server). Optional images.json:
    {"01.jpg": {"is_render": true, "role": "cover"|"gallery", "caption_en": "..."}}"""
    import json as _json

    meta = {}
    mf = folder / "images.json"
    if mf.exists():
        try:
            raw = _json.loads(mf.read_text(encoding="utf-8"))
            meta = {m["file"]: m for m in raw} if isinstance(raw, list) else raw
        except Exception as e:
            print(f"  ! could not read {mf.name}: {e}")
    files = sorted(f for f in folder.iterdir() if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    files.sort(key=lambda f: 0 if meta.get(f.name, {}).get("role") == "cover" else 1)
    out = []
    for f in files:
        try:
            im = Image.open(f)
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im, mask=im.getchannel("A"))
                im = bg
            im = im.convert("RGB")
        except Exception as e:
            print(f"  ! skipped {f.name}: {e}")
            continue
        if min(im.size) < MIN_SIDE:
            print(f"  ! skipped {f.name}: too small ({im.width}x{im.height})")
            continue
        if im.width > MAX_W:
            im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
        out.append((f.stem, im, bool(meta.get(f.name, {}).get("is_render", False)), meta.get(f.name, {}).get("caption_en", "")))
    return out[:max_images]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf-dir", required=True)
    ap.add_argument("--manifest", default=str(Path(__file__).with_name("portfolio_manifest.json")))
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--email")
    ap.add_argument("--password", default=os.getenv("ADMIN_PASSWORD"))
    ap.add_argument("--only", help="comma-separated slugs")
    ap.add_argument("--max-images", type=int, default=16)
    ap.add_argument("--min-side", type=int, default=700, help="ignore pictures smaller than this (px); lower it (e.g. 450) to catch more")
    ap.add_argument("--all-images", action="store_true", help="take EVERY large picture on a page, not just the biggest one")
    ap.add_argument("--images-dir", help="folder with one sub-folder per project slug (e.g. portfolio_export/images); used instead of the PDFs when present")
    ap.add_argument("--publish", action="store_true", help="make projects visible (default: hidden)")
    ap.add_argument("--replace-demo", action="store_true", help="delete the [placeholder] demo projects first")
    ap.add_argument("--dry-run", action="store_true", help="save previews to ./portfolio_preview, upload nothing")
    a = ap.parse_args()

    projects = json.load(open(a.manifest, encoding="utf-8"))
    if a.only:
        wanted = set(a.only.split(","))
        projects = [p for p in projects if p["slug"] in wanted]
    global MIN_SIDE
    MIN_SIDE = a.min_side
    pdf_dir = Path(a.pdf_dir)
    if a.all_images:
        for p_ in projects:
            p_["all_images"] = True

    s = requests.Session()
    existing: dict[str, int] = {}
    if not a.dry_run:
        if not a.email:
            sys.exit("--email is required (admin account)")
        pw = a.password or getpass.getpass("Admin password: ")
        r = s.post(f"{a.api}/api/admin/login", json={"email": a.email, "password": pw})
        if r.status_code != 200:
            sys.exit(f"Login failed: {r.text}")
        s.headers["Authorization"] = f"Bearer {r.json()['token']}"
        existing = {p["slug"]: p["id"] for p in s.get(f"{a.api}/api/admin/projects").json()}
        if a.replace_demo:
            for p in s.get(f"{a.api}/api/admin/projects").json():
                if p["title_en"].startswith("["):
                    s.delete(f"{a.api}/api/admin/projects/{p['id']}")
            for c in s.get(f"{a.api}/api/admin/clients").json():
                if c["name"].startswith("["):
                    s.delete(f"{a.api}/api/admin/clients/{c['id']}")

    sheet: list[str] = []
    for p in projects:
        src_label = "no files" if p.get("draft") or not (p.get("sources") or p.get("pdf")) else "; ".join(f"{x['pdf']} p.{x['pages'][0]}-{x['pages'][1]}" for x in (p.get("sources") or [p]))
        print(f"\n{p['title_en']}  ({src_label})")
        if p["slug"] in existing:
            print("  = already exists, skipped")
            continue
        folder = Path(a.images_dir) / p["slug"] if a.images_dir else None
        from_folder = bool(folder and folder.is_dir() and any(folder.iterdir()))
        if p.get("draft") and not from_folder:  # listed by the owner but no material yet: create a hidden placeholder to fill in /admin
            print("  draft (no photos yet)" + (f"   ? confirm: {p['confirm']}" if p.get("confirm") else ""))
            if not a.dry_run:
                body = {k: p.get(k, "") for k in ("slug", "title_en", "country", "type", "city_en", "scope_en", "summary_en", "is_render", "featured", "sort_order")}
                body["published"] = False
                r = s.post(f"{a.api}/api/admin/projects", json=body)
                print("  ✓ draft created (hidden)" if r.status_code == 201 else f"  ! create failed: {r.text}")
            continue
        imgs = load_folder(folder, a.max_images) if from_folder else collect(p, pdf_dir, a.max_images)
        if from_folder:
            src_label = f"folder {folder}"
        print(f"  {len(imgs)} images" + (f"   ? confirm: {p['confirm']}" if p.get("confirm") else ""))
        if not imgs:
            continue
        if a.dry_run:
            d = Path("portfolio_preview") / p["slug"]
            d.mkdir(parents=True, exist_ok=True)
            cells = []
            for i, (n, img, _, _c) in enumerate(imgs):
                img.thumbnail((900, 900))
                img.save(d / f"{i:03d}.jpg", quality=80)
                cells.append(f'<figure><img src="{p["slug"]}/{i:03d}.jpg" loading="lazy"><figcaption>page {n}</figcaption></figure>')
            sheet.append(
                f'<section><h2>{p["title_en"]} <small>{p["country"].upper()} · {p["type"]} · {"render" if p["is_render"] else "executed"} · '
                f'{src_label} · {len(imgs)} images</small></h2><div class="g">{"".join(cells)}</div></section>'
            )
            continue
        body = {k: p[k] for k in ("slug", "title_en", "country", "type", "city_en", "scope_en", "summary_en", "is_render", "featured", "sort_order")}
        body["published"] = a.publish
        r = s.post(f"{a.api}/api/admin/projects", json=body)
        if r.status_code != 201:
            print("  ! create failed:", r.text)
            continue
        pid = r.json()["id"]
        for i in range(0, len(imgs), 8):  # small batches keep requests light
            batch = imgs[i : i + 8]
            files = [("files", (f"{n}.jpg", jpeg_bytes(img), "image/jpeg")) for n, img, _, _c in batch]
            r = s.post(f"{a.api}/api/admin/projects/{pid}/images", files=files)
            if r.status_code != 201:
                print("  ! upload failed:", r.text)
                break
            for rec, (_, _, is_render, caption) in zip(r.json(), batch):  # per-image flags
                patch = {}
                if is_render and not p["is_render"]:
                    patch["is_render"] = True
                if caption:
                    patch["caption_en"] = caption
                if patch:
                    s.patch(f"{a.api}/api/admin/project-images/{rec['id']}", json=patch)
        print("  ✓ uploaded", "(published)" if a.publish else "(hidden: review in /admin)")

    if a.dry_run and sheet:
        html = (
            '<meta charset="utf-8"><title>Portfolio preview</title><style>body{font:14px system-ui;margin:24px;background:#fafaf8}'
            'h2{margin:32px 0 8px}small{font-weight:400;color:#666}.g{display:flex;flex-wrap:wrap;gap:8px}'
            'figure{margin:0;width:220px}img{width:220px;height:150px;object-fit:cover;border-radius:8px;background:#ddd}'
            'figcaption{font-size:12px;color:#666}</style><h1>Portfolio preview</h1>' + "".join(sheet)
        )
        Path("portfolio_preview/index.html").write_text(html, encoding="utf-8")
        print("\nOpen portfolio_preview\\index.html in your browser to review every project.")


if __name__ == "__main__":
    main()
