# Development audit and baseline

Date: 2026-10-18. Branch: `claude/wonderful-galileo-i8vhmd`, baseline commit `8beba28` (the report commit came after it).
Read alongside `PROJECT_REPORT.md`. This file records the state **before** the hardening programme and the checklist it worked from. The results are in `IMPLEMENTATION_REPORT.md`.

## 1. Baseline checks (executed)

| Check | Command | Result |
|---|---|---|
| Backend tests | `pytest -q` (backend) | 12 passed |
| Frontend type check + build | `npm run build` | OK. JS: main 32.6 kB, shared vendor 137.6 kB (45 kB gzip), admin chunk 24 kB (lazy). CSS: 64.6 kB (12.4 kB gzip). Routes are already lazy-loaded. |
| Python dependency audit | `pip-audit -r backend/requirements.txt` | No known vulnerabilities |
| JS dependency audit | `npm audit --omit=dev` | 2 moderate: react-router ≤ 7.17 (open redirect via backslash in `<Link>`/`navigate`; SSR deserialisation, which does not apply because there is no SSR). Fixed in 7.18.4 (major upgrade). |
| Static analysis | `ruff check backend` | Only FastAPI-idiom warnings (B008 `Depends` defaults) and md5 used for ETag. No ruff config in the repo. |
| Local database | `backend/*.db` | None in this environment. The owner's DB lives on Windows (`D:\Master Web (Redecor)\redecor-web`), so no backup could be taken here. Schema changes are therefore additive and applied by `ensure_columns()` at startup, which backs up the SQLite file first (added in this programme). |

## 2. What already exists and works (kept, not duplicated)
- Public pages: Home, Projects (filters by country and type), standalone project page, 4 service pages, About, Contact, Privacy, 404.
- EN/AR with RTL; dark/light theme toggle; empty media slots collapse; renders labelled.
- Admin: projects (all fields, multi-image upload, cover, layout, captions, order), clients, site image slots, offices, enquiries with status.
- Images: Pillow validation (format whitelist, 15 MB cap, pixel-bomb guard, EXIF strip), WebP variants, immutable caching, orphan cleanup.
- Auth: scrypt hashing, JWT HS256 with 12 h expiry, constant-time login with a dummy hash, IP rate limit on login (8 per 5 min), and on enquiries (5 per 10 min); honeypot field.
- Security headers: nosniff, `X-Frame-Options: DENY`, Referrer-Policy, Permissions-Policy. Validation errors never echo raw input.
- SEO: per-page `<title>`/description (client side), sitemap with hreflang, robots, absolute og:image.
- Deploy: Dockerfile, docker-compose with a `/data` volume, `.env.example`, DEPLOY.md, `tools/backup.py` (zip).

## 3. Findings (defects and gaps)

### Content integrity
1. `SEED_DEMO` **defaults to `1`** in `config.py`. A production start without `.env` would create `[Project name 01]`-style placeholder projects and clients.
2. `tools/seed_test_projects.py` creates TEST projects as **published**. Nothing on the server prevents test data from going public.
3. Public API filters only on `published`. A project or client whose title still contains `[placeholder]` text would be public.
4. Qatar office: address and hours are `[placeholders]`, and phone/WhatsApp equal the Egyptian number. The owner earlier confirmed that both offices share one number. Even so, the WhatsApp sheet and the Contact page present an Egyptian number under a "Qatar" label, which reads as a Qatari office line.
5. About stat "3 Regional bases" is unconfirmed (only 2 offices exist).
6. Arabic fallback shows English text inside RTL blocks without `lang`/`dir`, so mixed text is misaligned.

### Portfolio without images
7. A tile without a cover shows only the title (`tile--text`): no location, type or year. Projects page has no search. The mosaic was designed for images only.

### Contact / enquiries
8. **No notification** of new enquiries. They are only visible if someone opens the admin.
9. Duplicate submissions (double click on a slow network, reload and resend) create duplicate rows. No server-side deduplication.
10. Spam protection is honeypot plus IP limit only. There is no minimum fill-time check.
11. `service` is mandatory. That is acceptable, but `project_type`, area and message are already optional, so friction is reasonable.

### WhatsApp
12. Links open with no prefilled message and no page context; clicks are not measured.

### Security
13. JWT has no `iat`/token version, so sessions cannot be revoked (e.g. after a password change). `exp` is not explicitly required.
14. No production guard: the app starts with a random or empty `SECRET_KEY` and any `ADMIN_PASSWORD`. There is no password policy and no way to change the password from the admin.
15. Login is limited per IP only, not per account.
16. `/api/docs` and `/api/openapi.json` are public in production.
17. No Content-Security-Policy, no HSTS, no request body size limit (only per-upload checks after reading).
18. Docker runs uvicorn with `--forwarded-allow-ips=*` and publishes port 8000 directly. If the port is reachable, `X-Forwarded-For` can be spoofed to bypass rate limits. The container runs as root and has no health check.
19. Single role; every admin can do everything (no editor/viewer).

### Deployment and operations
20. `index.html` is read **once at startup**, so a new frontend build is not served until restart.
21. No HTTPS reverse proxy is provided (only documented). There is no log rotation or container health check.
22. Backups: zip of the raw SQLite file. With WAL mode this can miss committed data. No retention, verification, schedule or restore tool.
23. No monitoring beyond `/api/health` (no DB check, no error alerting).

### SEO / sharing
24. Social crawlers (WhatsApp, Facebook, LinkedIn) do not run JavaScript, so every URL shares the **homepage** title, description and image. Project pages have no project-specific preview.
25. Unknown URLs and unknown project slugs return **HTTP 200** (soft 404). There is no canonical link and no `hreflang` in the page head. There is no structured data.

### Project page / UX
26. No lightbox/zoom, no previous/next project, and no consultation CTA carrying the project context.
27. No analytics or conversion events.

### Admin workflow
28. No draft preview, no completeness indicator, no list search/filter, and no quick reordering. Delete confirmation is a plain `confirm()`.

### Code health
29. `styles.css` (~2,060 lines) carries several redesign layers and dead rules for removed components (old footer, old How-we-work sticky, service tiles, old client grid). `@fontsource/poppins` is still a dependency but unused.
30. No frontend automated tests; no lint config; no CI.

## 4. Prioritised implementation checklist
- **NOW:**
  - safe defaults (`SEED_DEMO=0`)
  - server-side publication guards (drafts, TEST, placeholders, unapproved clients)
  - office display rules (no Egyptian number under a Qatar label, no placeholders)
  - verified-only stats
  - Arabic fallback markup
  - typographic project tiles and search
  - form dedupe and min fill time
  - SMTP notifications with status, retries and no duplicates
  - WhatsApp context messages and click events
  - security hardening (JWT, production guard, password policy and change, per-account limit, docs off, CSP/HSTS, body limit, proxy trust, non-root container, health check)
  - fresh `index.html` without restart
  - Caddy HTTPS compose, log rotation
- **NEXT:**
  - project CTA with context, lightbox, previous/next
  - first-party privacy-friendly analytics with an admin view
  - server-side meta injection for every public route (titles, OG, canonical, hreflang, JSON-LD) and real 404 status
  - performance measurement
  - consistent SQLite backups with retention, verification, restore, schedule and off-server copy
  - deep health check and error alerts
- **LATER:**
  - roles (admin/editor/viewer) enforced on the backend, with user management
  - draft preview, completeness indicators, admin search/filter, reorder, safer delete
  - Arabic audit fixes
  - CSS dead-code removal, unused font dependency removed
  - downloadable company profile and approved testimonials (hidden until content exists)
- **QA:**
  - backend tests for every item above
  - Playwright end-to-end tests (desktop, tablet, mobile; EN/AR)
  - documentation set and launch gate
