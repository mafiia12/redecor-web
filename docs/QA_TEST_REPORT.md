# QA test report

Run date: 2026-10-18, in the development container (Linux, Python 3.13, Node 20, Chromium 1194).
Every result below comes from a command that was actually executed. Items that were **not** executed are listed in §5.

## 1. Summary
| Suite | Command | Result |
|---|---|---|
| Backend unit/API tests | `cd backend && python -m pytest -q` | **34 passed**, 0 failed |
| Backend lint (pyflakes, bugbear, bandit, pyupgrade, isort) | `cd backend && ruff check .` | **All checks passed** |
| Python dependency audit | `pip-audit -r backend/requirements.txt` | **No known vulnerabilities** |
| Frontend type check + production build | `cd frontend && npm run build` | **OK** (`tsc --noEmit` clean) |
| JS dependency audit | `npm audit --omit=dev` | **0 vulnerabilities** (was 2 moderate before the react-router upgrade) |
| End-to-end (Playwright) | `cd frontend && npx playwright test` | **49 passed**, 0 failed. Projects: desktop 1440×900, tablet 820×1180, mobile Pixel 7. |
| Production container smoke test | `docker build` + `docker run` with `APP_ENV=production` | **Passed** (§4) |

## 2. Backend tests (34)
- **Publication and content integrity:**
  - drafts, `test-project-*` and `[placeholder]` titles never appear on the public site, in the API or in the sitemap
  - `[placeholder]` text cannot be published
  - text-only projects are valid
  - clients need approval and a logo
  - testimonials need an approval record
  - the PDF stays hidden until published
  - placeholder office values are blanked
- **Enquiries:**
  - validation, honeypot and rate limit
  - bot timing check
  - duplicate submission stored once
  - stored with `not_configured` when there is no SMTP
- **Notifications:**
  - sent exactly once
  - failure recorded without credentials, then retried to success
  - manual resend refused after delivery
  - **real SMTP round trip** against a local `aiosmtpd` server (accepted, then server down, giving `failed`)
- **Auth and roles:**
  - all 43 admin endpoints return 401 without a token
  - viewer/editor/admin limits
  - last admin protected
  - role change and password change revoke old tokens
  - forged, expired and no-`exp` tokens rejected
  - per-account login limit
  - password policy
- **Platform:**
  - security headers and CSP
  - body size limit (413)
  - production configuration guard
  - JSON 404 for unknown API paths
  - 422 instead of 500 on a wrong content type
  - HEAD support for uptime monitors
  - deep health check
- **SEO:**
  - server-side `<title>`, description, canonical, hreflang and JSON-LD per page
  - Arabic `lang`/`dir`
  - real 404 for unknown pages and unpublished projects
  - `noindex` on admin and 404 pages
  - a new `index.html` build served without restart
- **Data:**
  - the forward migration adds columns to an old database, keeps rows, and writes a pre-migration backup
  - backup, verify, retention, off-site copy, corruption detection, and restore with "move aside"
- **Media:** responsive variants, cover rules, non-image rejection, immutable caching, logo endpoints.
- **Analytics, documents and admin workflow:**
  - anonymous event counters (bad names rejected, paths sanitised)
  - draft preview
  - bulk reorder
  - completeness indicator

## 3. End-to-end tests (49)
Data comes from a throw-away database seeded with text-only sample projects, so the site is tested without photography. One lightbox test uploads a plain grey PNG fixture to the temporary test database and deletes it afterwards.
- **Public site** (`public.spec.ts`):
  - identity and sections
  - no grey placeholder boxes
  - typographic tiles
  - publication rules (draft and TEST hidden, 404)
  - type filter (URL kept) and search
  - project page facts, server-rendered head, previous/next, and the "Ask about this project" link prefilling the form
  - service page related work
  - 404 page
  - EN↔AR switch (`dir`, `lang`; the unconfirmed stat is hidden)
  - theme toggle persists
  - placeholder Qatar office hidden
  - single WhatsApp destination with a context message `https://wa.me/201006602371?text=…<project>`
- **Contact** (`contact.spec.ts`):
  - accessible validation: alert, first invalid field focused, `aria-invalid`, `aria-describedby`
  - a real submission is stored exactly once with its notification status
- **Admin** (`admin.spec.ts`):
  - wrong password refused
  - draft → preview → publish flow, with the public URL returning 404 before publishing and 200 after
- **Accessibility** (`a11y.spec.ts`):
  - skip link is the first Tab stop
  - every image has `alt`
  - `lang` is correct per language
  - lightbox opens, shows 1/2, goes to 2/2 with the arrow key, closes with Esc and returns focus
- **Responsive** (`responsive.spec.ts`, desktop, tablet and mobile): no horizontal scroll and no console errors on 9 pages (EN and AR).
- **Mobile** (`mobile.spec.ts`): menu opens, Esc closes it, link navigation closes it; Arabic menu.
- **Performance budgets** (`perf.spec.ts`, local, unthrottled):

  | Page | CLS | First contentful paint | JS transferred (compressed) |
  |---|---|---|---|
  | `/` | 0.000 | 132 ms | 78 kB |
  | `/projects` | 0.000 | 192 ms | 80 kB |
  | `/projects/<slug>` | 0.010 | 204 ms | 81 kB |
  | `/ar` | 0.026 | 256 ms | 78 kB |

  Budgets: CLS < 0.1 and JS < 120 kB. These are local numbers; field numbers on a real connection will be higher.

  Build output:
  - main JS 166 kB (53.8 kB gzip)
  - CSS 60 kB (11.4 kB gzip; dead rules removed, 69 → 55 kB of source)
  - route chunks lazy-loaded
  - fonts subset by `unicode-range` (the Arabic font is downloaded only for Arabic text)

## 4. Production container smoke test (executed)
```
guard (no SECRET_KEY): "RuntimeError: Unsafe production configuration: SECRET_KEY must be ..."  exit 3
/api/health/ready: {"ok":true,"failed_notifications":0,"database":"ok","uploads":"ok","smtp_configured":false,"last_backup_hours":null}
headers: content-security-policy …, strict-transport-security: max-age=15552000, x-frame-options: DENY
/api/docs -> 404   /no-such-page -> 404
container user: uid=10001(redecor)
backup inside container: "OK redecor-backup-…zip: database 139264 bytes, 0 files"
docker health status: healthy
```
In this sandbox the image was built with a test-only CA certificate injected for the sandbox proxy. The committed `Dockerfile` is unchanged by that.

## 5. Not executed here (needs the owner's environment or accounts)
- **GitHub Actions** (`.github/workflows/ci.yml`): configured, not yet run on GitHub.
- **Real e-mail provider:** delivery through the company's SMTP provider has not been tested; credentials are pending. The code path is verified against a real local SMTP server.
- **Caddy HTTPS on the real domain:** certificate issuance and the DNS switch. These must not be done without owner approval.
- **Off-server backup destination:** none exists yet. The copy-and-verify logic itself is tested.
- **Restore test on the owner's real database:** procedure in BACKUP_AND_RECOVERY.md §5.
- **Lighthouse / field performance on a real network.**
- **Screen-reader manual pass** (NVDA/VoiceOver): automated checks only.
- **Browsers other than Chromium:** Firefox and Safari are not in the e2e projects. Add `devices["Desktop Firefox"]` and `devices["iPhone 14"]` when those browsers are installed.

## 6. How to run everything on Windows
```powershell
cd backend; .\.venv\Scripts\Activate.ps1; pip install -r requirements-dev.txt ruff pip-audit
python -m pytest -q; ruff check .; pip-audit -r requirements.txt
cd ..\frontend; npm install; npm run build; npx playwright install chromium
$env:PYTHON = "..\backend\.venv\Scripts\python.exe"; npx playwright test
```
