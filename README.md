# RE DECOR & MORE: Website (full stack)

React + TypeScript (Vite) frontend, FastAPI + SQLAlchemy backend. SQLite by default, PostgreSQL-ready via `DATABASE_URL`.
Implements the v1 design (Home, Projects, Case study, Services, Contact, About) in English and Arabic (RTL), plus a staff admin at `/admin`.

## Documentation
- **Project baseline and current state:** [docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md)
- **Audit, implementation, security, QA:** [DEVELOPMENT_AUDIT](docs/DEVELOPMENT_AUDIT.md), [IMPLEMENTATION_REPORT](docs/IMPLEMENTATION_REPORT.md), [SECURITY_REVIEW](docs/SECURITY_REVIEW.md), [QA_TEST_REPORT](docs/QA_TEST_REPORT.md)
- **Operations:** [DEPLOYMENT_GUIDE](docs/DEPLOYMENT_GUIDE.md), [BACKUP_AND_RECOVERY](docs/BACKUP_AND_RECOVERY.md)
- **Launch:** [LAUNCH_READINESS](docs/LAUNCH_READINESS.md), [DEFERRED_CONTENT](docs/DEFERRED_CONTENT.md)

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
Tests: `cd backend && pytest && ruff check .` · `cd frontend && npm run build && npx playwright test` (see docs/QA_TEST_REPORT.md).

## Production (single deployable)
Docker: `cp .env.example .env` (fill it in) then `docker compose up -d --build`. This runs Caddy (HTTPS), the site and a daily verified backup.
Full steps, SMTP and rollback: [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md). With `APP_ENV=production` the app refuses unsafe settings.
A new frontend build is served without restarting the backend.

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

## Importing client logos
`tools/import_clients.py` cuts each logo out of the "Our Clients" pages (Fit-out p.5-6 and Brief p.5-6), makes transparent PNGs, drops duplicates, and uploads them as clients:
```bash
python tools/import_clients.py --pdf-dir "D:\\Master Web (Redecor)" --dry-run      # preview in ./clients_preview
python tools/import_clients.py --pdf-dir "D:\\Master Web (Redecor)" --email ADMIN_EMAIL --names names.txt --replace-demo
```
`names.txt` = one client name per line, in the preview order (otherwise they are "Client 01"... and can be renamed in `/admin`).

## Performance choices
One `/api/bootstrap` call (ETag + sessionStorage) for first paint; route-level code splitting (admin code never loads on the public site); self-hosted fonts; lazy `srcset` images with reserved aspect ratios (no layout shift); gzip; reduced-motion respected.

## Deviations from the design (deliberate)
- Accent text/buttons use `#85673A` instead of `#9C7A45` so white-on-brass and brass-on-off-white pass WCAG AA; brand brass stays for focus/decoration.
- Built with React + FastAPI rather than the Next.js + Tailwind suggested in the design prompt.
- Three services shown (the fourth was a placeholder). "What's included" lists for Design and Supply are **draft copy to confirm**.
- Placeholder content stays in `[brackets]` (project names, About story, privacy policy, office details). Nothing was invented. Social icons appear only when URLs are set in `frontend/src/config.ts`.

## Security notes
scrypt password hashing, JWT (12 h) in sessionStorage, login and enquiry rate limits (in-memory, per process), honeypot, server-side validation, audit-log table for admin writes, security headers. Add a real privacy policy and email/WhatsApp notification of new enquiries before launch.


## Standalone project pages
Each project has its own Nuvelti-style page (black, narrow column): title, client logo banner, hero, tagline/summary, story (`## Heading` sections) and stacked photos; mark two consecutive photos as `Half` in /admin to show them side by side. Existing databases are migrated automatically on startup (`ensure_columns`). `images.json` in a server-render folder may also set `caption_ar` and `layout` (`full`/`half`).
