"""Create TWO clearly-marked TEST projects (with generated pictures and logo) to preview the final look of a project page.

    python tools/seed_test_projects.py --api http://localhost:8001 --email you@example.com
    python tools/seed_test_projects.py --api http://localhost:8001 --email you@example.com --delete   # remove them again

The pictures are drawn by this script (not real photos), every one is stamped "TEST IMAGE".
The server never shows "test-project-*" pages publicly unless ALLOW_TEST_CONTENT=1 is set (local preview only).
"""
import argparse
import getpass
import io
import os
import random
import sys

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1600, 1000


def _font(size):
    for f in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def grad(size, top, bottom):
    w, h = size
    im = Image.new("RGB", size)
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return im


def room(seed, wall, floor, accent, wide=True):
    rnd = random.Random(seed)
    w, h = (W, H) if wide else (H, int(H * 1.25))
    horizon = int(h * rnd.uniform(0.62, 0.7))
    im = grad((w, h), wall[0], wall[1])
    im.paste(grad((w, h - horizon), floor[0], floor[1]), (0, horizon))
    d = ImageDraw.Draw(im, "RGBA")
    # window with daylight
    ww, wh = int(w * rnd.uniform(0.25, 0.38)), int(horizon * 0.62)
    wx = int(w * rnd.choice([0.08, 0.55, 0.62]))
    wy = int(horizon * 0.12)
    d.rectangle([wx, wy, wx + ww, wy + wh], fill=(255, 244, 222, 255))
    for k in range(1, 3):
        d.line([(wx + ww * k // 3, wy), (wx + ww * k // 3, wy + wh)], fill=wall[0], width=6)
    d.rectangle([wx, wy, wx + ww, wy + wh], outline=wall[1], width=8)
    # light spill on the floor
    d.polygon([(wx, horizon), (wx + ww, horizon), (wx + ww + ww // 2, h), (wx - ww // 3, h)], fill=(255, 240, 210, 46))
    # sofa
    sx, sw = int(w * rnd.uniform(0.15, 0.4)), int(w * 0.34)
    sy = horizon - int(h * 0.1)
    d.rounded_rectangle([sx, sy, sx + sw, sy + int(h * 0.2)], 28, fill=accent + (255,))
    d.rounded_rectangle([sx - 20, sy - int(h * 0.07), sx + sw + 20, sy + 30], 28, fill=tuple(max(0, c - 18) for c in accent) + (255,))
    # rug and table
    d.ellipse([sx - 40, horizon + 30, sx + sw + 40, horizon + int(h * 0.15)], fill=(235, 228, 214, 200))
    d.ellipse([sx + sw // 3, horizon + 50, sx + sw // 3 + 150, horizon + 90], fill=(60, 52, 44, 255))
    # pendant lamps
    for _ in range(rnd.randint(2, 3)):
        lx = int(w * rnd.uniform(0.1, 0.9))
        d.line([(lx, 0), (lx, int(h * 0.2))], fill=(40, 40, 40, 255), width=3)
        d.ellipse([lx - 34, int(h * 0.2), lx + 34, int(h * 0.2) + 46], fill=(255, 226, 170, 255))
    # framed art
    ax = int(w * rnd.choice([0.3, 0.45, 0.8])) if wx > w * 0.4 else int(w * 0.72)
    d.rectangle([ax, int(horizon * 0.18), ax + 150, int(horizon * 0.18) + 200], fill=accent + (255,), outline=(30, 30, 30, 255), width=8)
    im = im.filter(ImageFilter.GaussianBlur(1.4))
    px = im.load()
    for _ in range(w * h // 28):  # film grain
        x, y = rnd.randrange(w), rnd.randrange(h)
        v = rnd.randint(-14, 14)
        r, g, b = px[x, y]
        px[x, y] = (max(0, min(255, r + v)), max(0, min(255, g + v)), max(0, min(255, b + v)))
    ImageDraw.Draw(im).text((24, h - 44), "TEST IMAGE", fill=(255, 255, 255), font=_font(22))
    return im


def jpg(im):
    b = io.BytesIO()
    im.save(b, "JPEG", quality=88)
    return b.getvalue()


def logo(text):
    im = Image.new("RGB", (640, 200), "white")
    d = ImageDraw.Draw(im)
    f = _font(54)
    box = d.textbbox((0, 0), text, font=f)
    d.text(((640 - box[2]) / 2, (200 - box[3]) / 2 - 6), text, fill=(30, 30, 30), font=f)
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


PALETTES = [
    ((226, 214, 196), (196, 180, 158)), ((70, 76, 84), (46, 50, 56)),
    ((232, 226, 218), (208, 198, 184)), ((52, 58, 52), (34, 38, 34)),
]
FLOORS = [((150, 118, 84), (106, 80, 56)), ((92, 92, 96), (64, 64, 68))]
ACCENTS = [(122, 138, 112), (176, 120, 84), (84, 104, 132), (150, 150, 150)]

PROJECTS = [
    dict(
        slug="test-project-a", title_en="Test Project A", title_ar="مشروع تجريبي أ", country="eg", type="office",
        city_en="New Cairo", city_ar="القاهرة الجديدة", year=2025, area_m2=1800, featured=True, sort_order=1,
        scope_en="Interior design and fit-out", scope_ar="تصميم داخلي وتنفيذ تشطيبات",
        client_name="Test Client A",
        tagline_en="A workplace designed around its people", tagline_ar="مكان عمل مصمم حول فريقه",
        summary_en="Headquarters offices for a technology company: open collaboration areas, quiet rooms and a double-height reception.",
        summary_ar="مقر إداري لشركة تقنية: مساحات عمل مفتوحة وغرف هادئة واستقبال بارتفاع مزدوج.",
        details_en="Client: Test Client A\nLocation: New Cairo, Egypt\nArea: 1,800 m²\nYear: 2025\nScope: Design, fit-out, joinery\nStatus: Delivered",
        details_ar="العميل: عميل تجريبي أ\nالموقع: القاهرة الجديدة، مصر\nالمساحة: ١٬٨٠٠ م²\nالسنة: ٢٠٢٥\nالنطاق: تصميم وتنفيذ ونجارة\nالحالة: تم التسليم",
        story_en="## Design Concept\n\nThe plan opens around a central atrium so daylight reaches every desk. Warm timber and stone tie the floors together.\n\nMeeting rooms sit along the façade, with soft acoustic finishes behind glass.\n\n## Vision\n\nAn office that feels like a place people choose to come to.",
        story_ar="## فكرة التصميم\n\nيتوزع المسقط حول بهو مركزي ليصل ضوء النهار إلى كل مكتب. الخشب الدافئ والحجر يربطان الأدوار ببعضها.\n\nغرف الاجتماعات على الواجهة بتشطيبات صوتية ناعمة خلف الزجاج.\n\n## الرؤية\n\nمكتب يشعر فيه الناس أنه مكان يختارون القدوم إليه.",
        seed=11, pal=0,
    ),
    dict(
        slug="test-project-b", title_en="Test Project B", title_ar="مشروع تجريبي ب", country="eg", type="residential",
        city_en="Sheikh Zayed", city_ar="الشيخ زايد", year=2024, area_m2=420, featured=True, sort_order=2,
        scope_en="Interior design, execution, furniture", scope_ar="تصميم داخلي وتنفيذ وأثاث",
        client_name="Test Client B",
        tagline_en="A family villa with a calm, warm character", tagline_ar="فيلا عائلية بطابع هادئ ودافئ",
        summary_en="A three-level villa: open living areas, a private family wing and a landscaped terrace.",
        summary_ar="فيلا من ثلاثة أدوار: مناطق معيشة مفتوحة وجناح عائلي خاص وتراس منسّق.",
        details_en="Client: Test Client B\nLocation: Sheikh Zayed, Egypt\nArea: 420 m²\nYear: 2024\nScope: Design, execution, furniture\nStatus: Delivered",
        details_ar="العميل: عميل تجريبي ب\nالموقع: الشيخ زايد، مصر\nالمساحة: ٤٢٠ م²\nالسنة: ٢٠٢٤\nالنطاق: تصميم وتنفيذ وأثاث\nالحالة: تم التسليم",
        story_en="## Design Concept\n\nNeutral stone and oak, with one accent colour per room. Every room opens to the garden.\n\n## Vision\n\nA home that stays quiet, and ages well.",
        story_ar="## فكرة التصميم\n\nحجر محايد وخشب بلوط مع لون مميز لكل غرفة. كل غرفة تفتح على الحديقة.\n\n## الرؤية\n\nبيت هادئ يحافظ على جماله مع الزمن.",
        seed=27, pal=2,
    ),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--email", required=True)
    ap.add_argument("--password", default=os.getenv("ADMIN_PASSWORD"))
    ap.add_argument("--delete", action="store_true", help="remove the test projects")
    a = ap.parse_args()
    s = requests.Session()
    r = s.post(f"{a.api}/api/admin/login", json={"email": a.email, "password": a.password or getpass.getpass("Admin password: ")})
    if r.status_code != 200:
        sys.exit(f"Login failed: {r.text}")
    s.headers["Authorization"] = f"Bearer {r.json()['token']}"
    mine = {p["slug"]: p["id"] for p in s.get(f"{a.api}/api/admin/projects").json() if p["slug"].startswith("test-project-")}
    for slug, pid in mine.items():
        if a.delete or slug in {p["slug"] for p in PROJECTS}:
            s.delete(f"{a.api}/api/admin/projects/{pid}")
            print("removed", slug)
    if a.delete:
        return
    for p in PROJECTS:
        body = {k: v for k, v in p.items() if k not in ("seed", "pal")}
        body["published"] = True
        r = s.post(f"{a.api}/api/admin/projects", json=body)
        if r.status_code != 201:
            print("create failed:", r.text)
            continue
        pid = r.json()["id"]
        wall = PALETTES[p["pal"]]
        wall2 = PALETTES[p["pal"] + 1]
        imgs = []
        for i in range(7):
            pal = wall if i % 2 == 0 else wall2
            imgs.append(room(p["seed"] * 10 + i, pal, FLOORS[i % 2], ACCENTS[(i + p["seed"]) % 4], wide=i not in (4, 5)))
        files = [("files", (f"{i}.jpg", jpg(im), "image/jpeg")) for i, im in enumerate(imgs)]
        recs = s.post(f"{a.api}/api/admin/projects/{pid}/images", files=files).json()
        for i, rec in enumerate(recs):
            patch = {"is_render": True}
            if i in (4, 5):
                patch["layout"] = "half"
            if i in (1, 3):
                patch["caption_en"] = "Living area" if i == 1 else "Reception"
                patch["caption_ar"] = "منطقة المعيشة" if i == 1 else "الاستقبال"
            s.patch(f"{a.api}/api/admin/project-images/{rec['id']}", json=patch)
        s.post(f"{a.api}/api/admin/projects/{pid}/logo", files={"file": ("logo.png", logo(p["client_name"].upper()), "image/png")})
        print("created", p["slug"])
    print("Created. They are visible only on a server started with ALLOW_TEST_CONTENT=1 (never in production).")
    print("Preview them in /admin (Preview button). Remove with --delete.")


if __name__ == "__main__":
    main()
