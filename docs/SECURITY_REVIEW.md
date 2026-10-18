# Security review

Scope: FastAPI backend, React site and admin, the Docker/Caddy deployment files, and the operator tools.
Method: code reading, automated tests (`backend/tests`, `frontend/e2e`), `pip-audit`, `npm audit`, `ruff` (bandit rules), and a production-mode container smoke test.
This is a practical review for a small company website. It is not a penetration test.

## Findings and remediation
| # | Area | Finding (before) | Fix | Verified by |
|---|---|---|---|---|
| 1 | Secrets | The app started with a random or empty `SECRET_KEY` in any environment | `APP_ENV=production` refuses to start without a configured 32+ character key, with `SEED_DEMO`/`ALLOW_TEST_CONTENT` on, without an `https` `SITE_URL`, or with a weak `ADMIN_PASSWORD` | `test_production_guard`; container run without a key exits with "Unsafe production configuration" |
| 2 | Sessions | JWT had no `iat` or version. A password change did not sign out other sessions. | Tokens carry `iat`, `exp`, `sub` and `ver`. `exp`/`iat`/`sub` are required. `ver` must match `users.token_version`, which is bumped on password or role change. | `test_password_change_revokes_old_sessions`, `test_tampered_or_expired_tokens_are_rejected` |
| 3 | Passwords | No policy, no change-password function | 12+ characters, letters plus digits/symbols, no e-mail name or common words. Applies to new users, password changes and the production admin. Own password change in /admin → My account. | `test_roles_are_enforced_on_the_server`, `test_password_change_revokes_old_sessions` |
| 4 | Brute force | Login limited per IP only | Per IP (8 per 5 min) **and** per account (10 per 15 min). Constant-time check with a dummy hash for unknown e-mails. | `test_login_is_limited_per_account`, `test_login_rate_limit` |
| 5 | Authorisation | Single role | Roles `admin` / `editor` / `viewer` enforced **on every admin endpoint on the server**. Viewers cannot read enquiries (personal data). Only admins manage users and office details. The last admin cannot be removed or demoted. | `test_every_admin_endpoint_requires_auth` (all 40+ admin routes return 401 without a token), `test_roles_are_enforced_on_the_server` |
| 6 | Headers | No CSP / HSTS / COOP | `Content-Security-Policy` (self only, no inline scripts, `frame-ancestors 'none'`), `Strict-Transport-Security` in production, `Cross-Origin-Opener-Policy`, `nosniff`, `X-Frame-Options: DENY`, Referrer- and Permissions-Policy. The uvicorn `Server` header is removed. | `test_body_limit_and_security_headers`; production container headers checked with curl |
| 7 | Request size | Uploads were checked only after reading the body | Content-Length ceilings checked before reading: 256 KB JSON, 30 MB single files, 120 MB multi-photo uploads. Caddy enforces 120 MB as well. | `test_body_limit_and_security_headers` |
| 8 | Uploads | (already good) format whitelist, 15 MB cap, pixel-bomb guard, EXIF stripped, re-encoded to WebP, random file names | Kept. The new PDF upload checks the `%PDF-` signature and a 25 MB cap, and stores the file under a random name. | `test_rejects_non_images`, `test_profile_document_and_testimonials_publish_rules` |
| 9 | Path traversal | SPA file serving resolves paths and checks they stay inside `dist` | Kept. `/api/`, `/media/` and `/assets/` are never served by the SPA fallback. | code review; unknown-path tests return 404 |
| 10 | Errors | Validation errors could echo raw bytes and crash. Unhandled errors returned plain text. | Validation output never echoes input. Unhandled errors return `{"detail": "Internal server error", "request_id": ...}`; the stack trace goes to the server log only and an optional alert is sent. | `test_wrong_content_type_is_422_not_500` |
| 11 | API docs | `/api/docs` and `/api/openapi.json` were public | Disabled in production | container smoke test (404) |
| 12 | Proxy trust | `--forwarded-allow-ips=*` with port 8000 published, so `X-Forwarded-For` could be spoofed to dodge rate limits | Port 8000 is bound to `127.0.0.1`; only Caddy (internal network) reaches the app and sets the forwarded headers | `docker-compose.yml` review |
| 13 | Container | Ran as root; no health check | Runs as unprivileged `redecor` (uid 10001), writable `/data` only, HEALTHCHECK on `/api/health/ready` | container smoke test: `uid=10001`, status `healthy` |
| 14 | Data exposure | Placeholder office data and test projects could reach the public site | A single public filter (`app/visibility.py`) hides drafts, `test-project-*`, `[placeholder]` titles, unapproved or logo-less clients, and unapproved testimonials. Bracketed office values are blanked. | `test_drafts_test_and_placeholder_projects_stay_private`, `test_clients_need_approval_and_a_logo`, e2e publication tests |
| 15 | Spam / abuse | Honeypot and IP limit only | Plus a minimum fill time (bots posting under 2.5 s are silently dropped) and duplicate suppression (same content within 30 min is stored once and e-mailed once) | `test_enquiry_bot_timing_and_duplicates` |
| 16 | Notification secrets | n/a | SMTP password only from the environment, masked in stored error messages, never logged | `test_notifications_sent_once_failures_kept_and_retried` |
| 17 | Analytics privacy | n/a | First-party counters only: event, path, language and day. No cookies, IPs, user agents or identifiers are stored. Do-Not-Track/GPC are honoured. Admin pages are not counted. | `test_events_are_anonymous_counters` |
| 18 | Webhooks | n/a | Alert webhook must be `https://` (no `file:` or other schemes) and is rate-limited per alert kind | code review |
| 19 | Dependencies | `npm audit`: 2 moderate (react-router ≤ 7.17 open redirect via backslash in `<Link>`) | Upgraded to react-router-dom 7.18.4. `npm audit` and `pip-audit` report 0 known vulnerabilities. Removed the unused Poppins font package. | `npm audit --omit=dev`, `pip-audit -r backend/requirements.txt` |
| 20 | CORS | Off by default; explicit origins only | Kept | config review |

## Remaining risks and recommendations
- **Token storage:** the admin token is kept in `sessionStorage`, not an httpOnly cookie. The strict CSP (no inline or third-party scripts) is the main XSS mitigation. Moving to httpOnly cookies with CSRF protection would be a larger change; it is not needed at this size.
- **Rate limits:** they are in memory, per process. That is correct for one container. If the site is ever scaled to several workers or servers, use a shared store or Caddy rate limiting.
- **CSP:** `style-src` includes `'unsafe-inline'` because React inline `style` attributes are used. Scripts remain `'self'` only.
- **Two-factor login:** not implemented. Keep admin accounts few, use strong unique passwords, and remove accounts of people who leave.
- **Admin paths:** `/admin` is linked from the footer ("Staff login"). That is acceptable with the controls above, and it can be removed from the footer if preferred.
- **Server hardening:** this is the hosting company's responsibility. Use SSH keys (no password login), automatic security updates, and a firewall allowing only 22/80/443.
- **Logo permission:** logos are a legal and permission matter, not a technical one. New and imported client logos start unpublished. The 16 logos already imported locally are published in the owner's database: confirm permission (especially Fertiglobe/ADNOC) before launch.

## Batch 2 additions

| # | Area | What was added | Evidence |
|---|---|---|---|
| 21 | Quote attachments | Type decided from the **bytes**, not the extension: PDF, DWG, DXF, XLSX, XLS, DOCX, JPG, PNG, ZIP only. Refused: macro-enabled Office files (`vbaProject.bin`, `macroEnabled` content types, `.xlsm/.docm…`, VBA in old `.xls`), executables and scripts inside ZIPs, nested archives, absolute or `../` paths, more than 500 entries, more than 300 MB uncompressed, compression ratio above 100 (zip bomb). ZIPs are inspected from the central directory only, never extracted. | `tests/test_batch2_attachments.py` (allowed and dangerous file matrices) |
| 22 | Attachment limits | 3 files, 15 MB each, 30 MB total (env-configurable). Enforced three times: Caddy `request_body max_size 32MB` for `/api/enquiries*`, the app's Content-Length / streaming body ceiling, and per-file/total checks while reading (each upload is spooled to disk, read at most to the limit). Files are checked **before** anything is stored. | `test_limits_count_size_total_and_body`, `test_bad_file_is_refused_and_nothing_is_stored` |
| 23 | Attachment storage | Random 32-hex names in `ATTACHMENTS_DIR` (own Docker volume `redecor-attachments`), outside `UPLOAD_DIR`; the app refuses to start if it is inside it. The original name is kept only as cleaned display metadata. Never served by `/media`. Included in backups. | `test_quote_with_files_is_stored_privately_and_downloadable_by_admin_only`, `test_backup_includes_attachments` |
| 24 | Attachment download | Admin only; `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff`, a fixed safe content type per detected kind, `Cache-Control: private, no-store`; every download written to the audit log; files flagged as infected cannot be downloaded. Notification and digest e-mails show only the number of files. | same test, `test_virus_scan_results` |
| 25 | Virus scanning | Optional ClamAV (`VIRUS_SCAN_ENABLED=1`, compose profile `virus-scan`). The enquiry is stored first; a scanner error only marks the file `error`, never deletes the enquiry. With scanning off every file stays in state `quarantine` and the admin sees "Not scanned: open with care". | `test_virus_scan_results`, `test_scanner_down_never_loses_the_enquiry` |
| 26 | Enquiries access | Enquiries (personal data) are now **admin-only** (editors no longer see them). Assignment only to admin accounts. CRM history is append-only. | `test_enquiries_are_admin_only`, `test_status_workflow_with_append_only_history` |
| 27 | Spreadsheet exports | Every exported cell starting with `= + - @`, tab or CR is prefixed with `'` (formula injection), CSV and XLSX. | `test_export_protects_against_formula_injection` |
| 28 | Approval evidence | Evidence files use the same content checks and private store; download needs an editor login and is audited. | `test_gate_for_client_logos_and_evidence_file` |
| 29 | Health endpoint | Public `/api/health/ready` returns only `{"ok": true}` (200) or `{"ok": false}` (503); details need `HEALTH_TOKEN` or an admin token. | `test_batch2_deploy.py` |

### ClamAV trade-off
ClamAV keeps its signature database in memory: plan for **about 1–1.5 GB of extra RAM** (and ~300 MB disk for
`clamav-db`), plus a few minutes at start while signatures load. On a 1–2 GB VPS that is too much; options:
1. keep `VIRUS_SCAN_ENABLED=0` (default). Files stay marked *not scanned*, staff open them with care on an updated
   machine with antivirus, and the content checks above still refuse executables, macros and archive tricks;
2. move to a 4 GB server and enable the `virus-scan` profile;
3. scan on the staff PC (Windows Defender scans downloads automatically).
Recommendation: option 1 at launch, option 2 if attachment volume grows.

### Data retention (enquiries and attachments)
Enquiries and their files are personal data. Suggested policy (owner to confirm, then it can be automated):
keep **won** enquiries with the project file as required for contracts/accounting; delete **lost** and **spam**
enquiries and their attachments after **12 months**, and any enquiry with no reply after 24 months. Deletion is
not automated in this batch (no rows are ever deleted by the system). Backups keep deleted data until they rotate
out (`BACKUP_KEEP`, default 14 days).
