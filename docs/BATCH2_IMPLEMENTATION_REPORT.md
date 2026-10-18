# Batch 2 implementation report — admin tooling, approvals, enquiries CRM, deploy prep

Branch: `feat/batch2-admin-tools` (not merged, not deployed). Base: `46c0485`.
Nothing was deployed. DNS, domain, nameservers, GoDaddy, Vercel, Zoho and MX/SPF/DKIM were not touched.
Arabic text is not reproduced in this report; dictionary keys are named instead.

Commits (one per phase):

| Commit | Phase |
|---|---|
| `e44e1fa` | A — migrations, env validator, smoke test, staging, runbook items |
| `add2e9a` | B — bulk photos, quality rules, labels, focal point, approvals gate, readiness |
| `ffcdbc6` | C1 — project import |
| `731a839` | C2 — enquiries CRM and daily digest |
| `a27e679` | C3 — quote-form attachments |
| `9019be6` | Final checks, env examples, i18n check, docs |

## 1. Features

| # | Feature | Status | How it was verified |
|---|---|---|---|
| A1 | `tools/check_env.py` (types, required in production, partial SMTP, weak/dev secrets, file mode 600, `ENFORCE_APPROVALS=0` refused in production) | Done | 23 unit tests in `test_check_env.py` (one or more per fail rule); `.env.example` → exit 1 with 3 fails; a valid env → exit 0 |
| A2 | `tools/smoke_test.py --base-url` (read-only GET/HEAD, JSON result) | Done | 26/26 passed against the local Docker stack (Caddy + web + backup) |
| A3 | `docker-compose.staging.yml`, `.env.staging.example`, DEPLOYMENT_GUIDE §5b Staging | Done | Staging started next to the local stack; `docker volume ls` shows `redecor-staging-data`, `redecor-staging-attachments` separate from `redecor-local_*` (§3) |
| A4 | Five runbook items | Done | §5 |
| B1 | Bulk photo upload: admin page + `tools/bulk_images.py`, naming `<slug>__<nn>__<render\|executed>[__cover].<ext>`, optional CSV, dry-run by default, confirm/`--apply`, SHA-256 dedupe, automatic DB backup, import log | Done | `test_batch2_content.py` (dry-run writes nothing, apply, re-run idempotent, zip + CSV, CLI dry-run); e2e: dry run → confirm in the admin |
| B1 | Quality rules (1600 px gallery / 2400 px cover, aspect 0.5–2.4, content sniffing, size), EXIF/GPS stripped, orientation applied, override recorded with who/when | Done | `test_quality_rules_override_and_exif` |
| B1 | Render/Executed label mandatory, no default, project cannot be published with an unlabelled photo; public render badge via keys `projects.render`, `projects.renderShort` | Done | `test_kind_is_required_to_publish_and_hidden_without_it` |
| B1 | Focal point (click) → `object-position` on the public site; per-photo alt text EN/AR | Done | e2e: click at 20%/30% → public image style `object-position: 20% 30%` |
| B1 | `docs/CONTENT_GUIDE.md` | Done | — |
| B2 | Approvals register: append-only table, history, evidence file (private, audited download), gate in the public API on the server, `ENFORCE_APPROVALS=1` default, `0` refused in production by app and `check_env` | Done | `test_gate_*` (5 tests), e2e: project appears only after the approval is recorded |
| B2 | Dry-run report of what the gate hides (`tools/approval_gate_report.py`, admin endpoint) | Done | `test_gate_report_lists_only_what_the_gate_hides`; run on a pre-batch-2 DB copy (§4) |
| B3 | Readiness dashboard (title/desc AR+EN, cover, photo count, all labelled, alt EN/AR, approval, published, ready; filter not ready, sort by missing, "X of Y", CSV/XLSX) | Done | `test_readiness_is_computed_and_exports` |
| C1 | Import from XLSX/CSV/JSON manifest: template + Instructions sheet, per-row/per-cell errors, created as drafts, update only with explicit option (filled cells only), backup first, import log + audit log, UTF-8 with/without BOM | Done | `test_batch2_import.py` (9 tests incl. Arabic round trip CSV with BOM, without BOM, XLSX; cp1256 refused with advice); e2e CSV dry run → confirm |
| C2 | Enquiries CRM: workflow new→contacted→quoted→won/lost/spam (legacy `closed` kept), append-only history with user and time, assignee (admins), next follow-up + overdue badge, internal notes, source page, language, filters (status, assignee, overdue, date, language), search, formula-safe CSV/XLSX export, admin-only | Done | `test_batch2_crm.py` (11 tests); e2e status change + note in history |
| C2 | Daily digest to `NOTIFY_TO` via the existing mailer, scheduled inside the stack (`DIGEST_TIME`, `DIGEST_TZ` default Africa/Cairo), once per day (job_runs claim), SMTP missing → logged and skipped, `tools/digest.py --dry-run` | Done | digest tests: dry run records nothing; no SMTP → skipped once per day; real SMTP (aiosmtpd) → sent once, second call skipped, no attachment parts; time-zone schedule |
| C2 | Retention note | Done | SECURITY_REVIEW.md "Data retention" |
| C3 | Quote attachments: content whitelist, macro/executable/nested/traversal/zip-bomb refusal, 3 files / 15 MB / 30 MB (env), Caddy + app limits, random names in a private volume, original name as cleaned metadata, backup/restore include it, admin-only download (attachment, nosniff, safe type, no-store), every download audited | Done | `test_batch2_attachments.py` (26 cases); e2e upload + admin download |
| C3 | Optional ClamAV (`VIRUS_SCAN_ENABLED`, compose profile `virus-scan`), quarantine state + warning when off, scan failure never deletes the enquiry, ClamAV RAM trade-off documented | Done | fake clamd tests (clean / infected → download blocked), scanner down → status `error`, enquiry kept |
| C3 | Form UX EN/AR (keys `form.files.*`), types and limits shown, per-file progress, remove before submit, friendly translated errors, mobile; digest and admin list show the attachment count; e-mails never include files | Done | e2e desktop EN; e2e mobile AR (RTL, 44 px remove target, no horizontal scroll, translated error) |

Not done / partial: none of the requested items. Limits of what could be verified are in §2.

## 2. Verification status

| Check | Result |
|---|---|
| Backend tests | **before 34 → after 146 passed** (`pytest -q`) |
| End-to-end (Playwright) | **before 49 → after 55 passed** (desktop, tablet, mobile projects) |
| Lint | `ruff` clean on `backend/app`, `backend/tests` and the new tools |
| Typecheck / build | `tsc --noEmit` clean; `vite build` OK |
| i18n dictionary check | new `npm run check:i18n`: 268 keys, EN and AR match (shown to fail on a copy with one AR key removed) |
| `check_env` on `.env.example` | exit 1: `SECRET_KEY` required, `ADMIN_EMAIL` required in production, file mode too open (as intended) |
| `check_env` on a valid env | exit 0 (1 warning: `ADMIN_PASSWORD` empty is fine after first run); same file with `ENFORCE_APPROVALS=0` → FAIL |
| Docker | image built; local stack (caddy + web + backup) up, web healthy; `smoke_test.py` 26/26; Caddyfile `caddy validate` OK |
| Staging compose | up next to the local stack with separate named volumes; `X-Robots-Tag: noindex, nofollow` on staging, absent on the primary host |
| Migrations | up → down 4 → up on a copy of a database created by the pre-batch-2 code, verified backup before each step (§3) |
| Git hygiene | no `.env`, `.db`, backups, uploads or attachments in the branch; runtime folders added to `.gitignore`. The only secret-like strings added are fake fixtures in `backend/tests/test_check_env.py` |

Not verified here (needs the owner's machine): running the gate report and the migrations on the **owner's own**
database, which is not reachable from this environment (§4, §9).

## 3. Migrations

Versioned, reversible, recorded in table `schema_migrations` (`backend/app/migrations.py`). The app applies pending
migrations at start after a SQLite copy `<db>.pre-migrate-<time>.bak`; `python tools/migrate.py up|down|status`
takes a full verified `tools/backup.py` archive first and stops if it is missing or empty.
All changes are additive: new tables and new nullable columns only; nothing dropped, renamed or retyped; no rows deleted.

| Id | Change | Downgrade |
|---|---|---|
| 0001_baseline | adopts the existing tables (creates only missing ones / missing columns) | refused by design (it is the starting point) |
| 0002_media_quality | `images.sha256`; `project_images.kind, focal_x, focal_y, alt_en, alt_ar, quality_warnings, quality_override_by, quality_override_at`; backfill `kind='render'` only where `is_render=1` | tested |
| 0003_approvals | table `approvals` | tested |
| 0004_crm_attachments | `enquiries.assigned_to_id, next_follow_up, source_page`; tables `enquiry_events`, `enquiry_attachments`, `job_runs` | tested |
| 0005_import_log | table `import_log` | tested |

Up/down/up run (log: scratchpad `mig/migration_run.txt`): database created by commit `46c0485` with demo seed plus
two photos (one marked render) and one old enquiry (status `closed`).
Backups: `redecor-backup-20261018-142109.zip`, `…142110.zip`, `…142111.zip` (verified, non-empty).
Afterwards: projects 9, photos 2, clients 12, enquiries 1, users 1 (unchanged); the render photo has `kind=render`, the
other `kind` empty; the old enquiry kept `closed`; `PRAGMA integrity_check` = ok.

## 4. Approval gate impact (constraint 5)

What the gate changes on the public site, measured with `python tools/approval_gate_report.py` (read-only):
items that pass every other public rule (published, no `[placeholder]`, not `test-project-*`, logo present) but have
no current approval, and photos with no Render/Executed label.

* **Measured here** on a copy of a pre-batch-2 database (demo seed): 0 projects, 0 logos, 0 photos — the demo rows
  are placeholders and were never public.
* **Owner's database: not measurable from this environment.** Expected from earlier sessions (to be confirmed by
  running the report): all **16 published client logos** imported from the client slide will be hidden until a
  *Logo usage permission* is recorded for each — National Bank of Egypt, Seven Fortunes Coffee Roasters, Tanmeyah,
  Kasrawy Group, i Score, Fertiglobe, Be Babel, Banque Misr, Sokkar Mecca, Chai Jmr, Systel, Andalusia Hospitals,
  Modad Properties, Sheraton, ADNOC, ADD Properties (names as in `tools/client_names.txt`); and **every published
  project** until a *Client permission to publish* is recorded. Portfolio projects imported with
  `tools/import_portfolio.py` were created hidden unless `--publish` was used. Photos already marked as renders keep
  showing (backfilled `render`); photos without that mark are hidden until labelled.
* Owner command (after `python tools/migrate.py up`, which backs up first):
  `python tools/approval_gate_report.py` — or Admin → Readiness / the approvals gate report endpoint.

## 5. Runbook items (A4)

| Item | Before | Now | Evidence |
|---|---|---|---|
| Public health shows only ok / 503 | **Fixed**: `/api/health/ready` exposed database/storage/backlog details publicly | `{"ok": true}` 200 or `{"ok": false}` 503; details with `HEALTH_TOKEN` header or an admin token | `test_batch2_deploy.py`; smoke test |
| `X-Robots-Tag: noindex` when `SITE_DOMAIN` ≠ primary | **Fixed** (new) | every response on a non-primary host | test + staging curl |
| Caddy www → apex from env | **Already fine** | `www.{$SITE_DOMAIN}` → `{$SITE_DOMAIN}` 301 | `caddy adapt` output |
| Start without `ADMIN_PASSWORD` once an admin exists | **Already fine** (password only used to create the first admin); added: production with zero users refuses to start with a clear message | restart of the Docker web service with `ADMIN_PASSWORD` removed → healthy | subprocess test + Docker restart |
| Config-driven 301 map | **Fixed** (new) | `REDIRECTS_FILE` (default `deploy/redirects.json`, empty `{}`), paths validated, GET/HEAD only | `test_batch2_deploy.py` |

## 6. New settings (all in `.env.example` and `backend/.env.example` with safe defaults; an empty value means "default")

| Variable | Default | Purpose |
|---|---|---|
| `PRIMARY_DOMAIN` | `redecorgroup.com` | other hosts get noindex |
| `HEALTH_TOKEN` | empty | unlocks detailed health output |
| `REDIRECTS_FILE` | `deploy/redirects.json` | 301 map |
| `ENFORCE_APPROVALS` | `1` | publication gate (`0` refused in production) |
| `IMAGE_MIN_LONG_EDGE` / `IMAGE_MIN_COVER_LONG_EDGE` | `1600` / `2400` | photo quality |
| `IMAGE_ASPECT_MIN` / `IMAGE_ASPECT_MAX` | `0.5` / `2.4` | photo quality |
| `ATTACHMENTS_DIR` | `backend/attachments`; Docker `/attachments` | private files (own volume) |
| `ATTACH_MAX_FILES` / `ATTACH_MAX_FILE_MB` / `ATTACH_MAX_TOTAL_MB` | `3` / `15` / `30` | quote attachments |
| `VIRUS_SCAN_ENABLED` / `CLAMAV_HOST` / `CLAMAV_PORT` | `0` / `clamav` / `3310` | optional ClamAV |
| `DIGEST_TIME` / `DIGEST_TZ` | empty (off) / `Africa/Cairo` | daily digest |

New Python dependencies: `openpyxl==3.1.5`, `tzdata==2026.5` (dev: `aiosmtpd==1.4.6`).

## 7. Project manifest (C1)

* Path: `tools/portfolio_manifest.json`, **59 rows**.
* Dry run on a throw-away test database: **59 create, 0 update, 0 skip, 0 error**. Extra keys (`pages`, `pdf`,
  `sources`, `confirm`, `draft`, `scope`, `all_images`) are ignored and reported per row. Nothing was written.
* On the owner's database, projects already imported earlier will show as **skip** (same slug) unless
  "update existing" is chosen.

## 8. Decisions and risks

* **Enquiries are now admin-only** (spec). Editors lose access they had before; the old test was updated.
* **Unlabelled photos are hidden publicly** (no guessing "executed"); the gate report counts them.
* **Deleting a project/client appends a `revoked` approval** — found by e2e: SQLite reuses ids, so a new item could
  otherwise inherit a deleted item's approval.
* **Gate query bug found and fixed**: a newer approval of any project hid older approvals of others.
* Admin-only image fields (who overrode the quality check, quality notes) are kept out of the public API (test-covered).
* Digest failures are logged and not retried the same day (no e-mail storm); the scheduler runs in the web process
  and the `job_runs` claim prevents duplicates across restarts or workers.
* Caddy's active health check marks the app down until the first successful check (up to ~30 s after a start or
  restart, visitors get 503). Pre-existing; proposal: add `health_interval 5s` in `deploy/Caddyfile` (not changed here).
* ClamAV needs ~1–1.5 GB RAM; off by default, files then show "not scanned" (SECURITY_REVIEW.md).
* Arabic dictionary text for the file field (`form.files.*`) should be reviewed by a native speaker.
* Attachments are scanned in a background task after the response; on a very slow scanner the e-mail waits for it.

## 9. Owner input needed (placeholders)

1. Record approvals (with evidence) for every client logo and project that should stay public, before enabling this
   release on the live database (§4).
2. Run `python tools/migrate.py up` and `python tools/approval_gate_report.py` on the real database and keep the output.
3. Decide `DIGEST_TIME`, `NOTIFY_TO`, and whether to enable ClamAV (server RAM).
4. Confirm the retention policy (SECURITY_REVIEW.md) before any deletion is automated.
5. Fill `deploy/redirects.json` with old-site URLs if any are known (currently empty).

## 10. Rollback

* **Code:** deploy the previous image/commit (`46c0485`). The new columns and tables are additive, so the old code
  runs on the migrated database (it ignores them).
* **Schema:** `python tools/migrate.py down --steps 4` (verified backup first) removes 0005…0002; baseline stays.
* **Data:** `tools/restore.py <backup.zip> --db … --uploads … --attachments …` (moves current data aside, never deletes);
  every migration, bulk upload and import made a backup first.
* **Gate only:** for local design work `ENFORCE_APPROVALS=0` (refused in production by design).
