# RE DECOR & MORE: Website (full stack)

React + TypeScript (Vite) frontend, FastAPI + SQLAlchemy backend. SQLite by default, PostgreSQL-ready via `DATABASE_URL`.
Implements the v1 design (Home, Projects, Case study, Services, Contact, About) in English and Arabic (RTL), plus a staff admin at `/admin`.

## Run (development)
```bash
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # set SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD
uvicorn app.main:app --reload --port 8000

# frontend (second terminal)
cd frontend && npm install && npm run dev     # http://localhost:5173 (proxies /api and /media)
```
Tests: `cd backend && pytest`. Type-check/build: `cd frontend && npm run build`.

## Production (single deployable)
`cd frontend && npm run build`, then run uvicorn from `backend/`. FastAPI serves `frontend/dist`, the API and `/media`.
Set `SITE_URL`, `SECRET_KEY`, `DATABASE_URL`, `SEED_DEMO=0`, and put it behind HTTPS.

## Adding project and client photos (next phase)
Sign in at `/admin` (footer "Staff Login"):
- **Projects**: create/edit, upload many photos (first = cover), flag renders ("Design visualization" badge), full-bleed, bilingual captions.
- **Clients**: add name + logo (shown grayscale in the wall).
- **Site images**: hero, service tiles/heroes, "How we work", About. Every slot shows a neutral placeholder until filled.
- **Offices**: real phone/WhatsApp/email/address. Placeholders like `[+20 XXX]` never become links.
- **Enquiries**: submitted forms with status (new / contacted / closed).

Uploads are validated, auto-rotated, metadata-stripped and converted to responsive WebP (480-2400 px) with a year-long immutable cache.

## Importing the portfolio PDFs (images + project data)
`tools/import_portfolio.py` pulls the best picture from each PDF page of a project (page ranges are in `tools/portfolio_manifest.json`) and uploads it through the admin API. Run it where the PDFs are, with the backend running:
```bash
pip install -r tools/requirements.txt
python tools/import_portfolio.py --pdf-dir "D:\Master Web (Redecor)" --dry-run     # previews in ./portfolio_preview
python tools/import_portfolio.py --pdf-dir "D:\Master Web (Redecor)" --email ADMIN_EMAIL --replace-demo
```
Projects are created hidden; review them in `/admin`, then tick Published (or rerun with `--publish`). Edit the manifest first if names, countries, types or page ranges are wrong.

## Performance choices
One `/api/bootstrap` call (ETag + sessionStorage) for first paint; route-level code splitting (admin code never loads on the public site); self-hosted fonts; lazy `srcset` images with reserved aspect ratios (no layout shift); gzip; reduced-motion respected.

## Deviations from the design (deliberate)
- Accent text/buttons use `#85673A` instead of `#9C7A45` so white-on-brass and brass-on-off-white pass WCAG AA; brand brass stays for focus/decoration.
- Built with React + FastAPI rather than the Next.js + Tailwind suggested in the design prompt.
- Three services shown (the fourth was a placeholder). "What's included" lists for Design and Supply are **draft copy to confirm**.
- Placeholder content stays in `[brackets]` (project names, About story, privacy policy, office details). Nothing was invented. Social icons appear only when URLs are set in `frontend/src/config.ts`.

## Security notes
scrypt password hashing, JWT (12 h) in sessionStorage, login and enquiry rate limits (in-memory, per process), honeypot, server-side validation, audit-log table for admin writes, security headers. Add a real privacy policy and email/WhatsApp notification of new enquiries before launch.
