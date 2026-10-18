# Launch readiness (gate)

Date: 2026-10-18. Evidence lives in `QA_TEST_REPORT.md`, `SECURITY_REVIEW.md` and `IMPLEMENTATION_REPORT.md`.

**Classification:**
- **PASS:** verified here.
- **FAIL:** a problem found.
- **BLOCKED (external):** needs the owner's server, accounts or credentials.
- **DEFERRED (owner):** postponed on purpose.

| # | Check | Result | Evidence / what is needed |
|---|---|---|---|
| 1 | Demo data disabled | **PASS** | `SEED_DEMO` defaults to 0 and production refuses 1. Placeholder rows are never public. |
| 2 | TEST projects unpublished or removed | **PASS** (code) / **BLOCKED (external)** (owner's data) | The server hides `test-project-*`, and production forbids `ALLOW_TEST_CONTENT`. The owner should still delete the two TEST projects from the local database (`tools/seed_test_projects.py --delete`), with their approval. |
| 3 | Admin account secure | **PASS** (mechanisms) / **BLOCKED (external)** | Password policy, rate limits, revocation and roles are tested. The production admin password must be newly chosen by the owner (not the one used in development). |
| 4 | Production secrets configured securely | **BLOCKED (external)** | `.env` on the server with a new `SECRET_KEY`. The app will not start with unsafe values (verified in the container). |
| 5 | Database and uploads persistent | **PASS** | Docker volume `redecor-data` at `/data`. Container test wrote the database and a backup there. |
| 6 | Backup mechanism tested | **PASS** (local and container) / **BLOCKED (external)** (off-server copy) | `test_backup.py`; backup run inside the production container. An off-server destination and a restore test on the real database are still needed. |
| 7 | Contact submissions stored correctly | **PASS** | Backend tests and e2e (stored once, status recorded) |
| 8 | E-mail notification tested | **PASS** (implementation, real local SMTP) / **BLOCKED (external)** (company provider) | Needs SMTP credentials and `NOTIFY_TO`, then /admin → Send test e-mail |
| 9 | WhatsApp routing validated | **PASS** | e2e: one destination `wa.me/201006602371` with a context message. Only one number exists today (shared by both offices, as instructed). |
| 10 | Public routes functional | **PASS** | e2e on 9 routes × 3 viewports; real 404s |
| 11 | Arabic and English interfaces tested | **PASS** | e2e AR/EN, `lang`/`dir`, AR screenshots; fixes applied |
| 12 | Mobile layouts verified | **PASS** | e2e Pixel 7 and tablet: no horizontal scroll, menu tests |
| 13 | SEO and sharing metadata inspected | **PASS** | Server-side head per page (tested), sitemap, robots, JSON-LD, canonical/hreflang. Final OG image URLs depend on `SITE_URL`. |
| 14 | Security review completed | **PASS** | `SECURITY_REVIEW.md`; 0 known dependency vulnerabilities |
| 15 | No broken internal navigation | **PASS** | e2e navigation tests; no console errors on tested pages |
| 16 | No unauthorized client logos or images | **BLOCKED (external)** | New and imported logos start unpublished. The 16 logos already published in the owner's local database need permission confirmed (Fertiglobe/ADNOC in particular), or must be unpublished. No project images are published. |
| 17 | No fabricated or unverified company information | **PASS** (code) / **BLOCKED (external)** (wording) | The unverified stat is hidden and placeholders are hidden. The Divisions texts are draft wording based on the company profile and must be approved by the owner (`frontend/src/content.ts`). |
| 18 | Production configuration documented | **PASS** | `DEPLOYMENT_GUIDE.md`, `.env.example` |
| 19 | Rollback procedures documented | **PASS** | `DEPLOYMENT_GUIDE.md` §7, `BACKUP_AND_RECOVERY.md` §4, pre-migration `.bak` |
| 20 | All critical tests passing | **PASS** | 34/34 backend, 49/49 e2e, lint and type checks clean |
| – | Real project photography and renders | **DEFERRED (owner)** | Not a failure. Text-only pages are designed for it. |

## Recommendation: **CONDITIONAL GO**
The code is production-ready and verified locally and in a production-mode container. Publishing the site publicly
must wait for these owner actions (none of them are code changes):
1. **Server:** rent the server, fill in `.env` (new `SECRET_KEY`, new admin password), run `docker compose up -d --build`, then point DNS to it.
2. **E-mail:** enter the SMTP credentials and send the test e-mail from the admin.
3. **Backups:** configure the off-server backup destination and do one restore test.
4. **Content:** approve or unpublish client logos; approve the Divisions wording; delete the TEST projects; publish real projects (text-only is fine).
5. **Monitoring:** create an uptime monitor on `/api/health/ready`.
