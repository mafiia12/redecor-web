# Implementation report

**Baseline:** `docs/DEVELOPMENT_AUDIT.md` (commit `8beba28`).

**Status key:**
- **Done:** implemented and tested locally.
- **Configured:** implemented, waiting for external setup or credentials to be used for real.
- **Owner:** waiting for company data or a decision.
- **Deferred:** postponed by the owner.

## Feature table
| # | Requested feature | Status | Main files | Verification | Remaining blocker |
|---|---|---|---|---|---|
| 1.1 | Drafts never public | Done | `app/visibility.py`, `routers/public.py`, `main.py` (sitemap), `seo.py` | `test_drafts_test_and_placeholder_projects_stay_private`; e2e publication test | – |
| 1.1 | Test projects never public | Done | `visibility.py` (`ALLOW_TEST_CONTENT`, off and enforced off in production), `tools/seed_test_projects.py` | same tests | – |
| 1.1 | `[placeholder]` content can't be published | Done | `routers/admin.py` (`_publish_guard`), `visibility.py` | same tests | – |
| 1.1 | Unapproved client logos unpublished | Done | `schemas.ClientIn.published=False`, `visibility.public_clients`, `tools/import_clients.py` (`--publish` opt-in) | `test_clients_need_approval_and_a_logo` | Owner: confirm the 16 logos already published locally |
| 1.1 | Empty media collapses | Done (already) | `components/Photo.tsx` | e2e "no grey placeholder boxes" | – |
| 1.1 | Controlled Arabic fallback | Done | `lib/context.tsx` (`loc()`), Cards, ProjectDetail, Testimonials, Lightbox | visual check, e2e AR pages | Owner: Arabic project texts |
| 1.1 | No unverified statistics | Done | `content.ts` (`STAT_CONFIRMED`), `pages/About.tsx` | e2e (2 stats in AR About) | Owner: confirm "3 regional bases" |
| 1.1 | Qatar must not show Egyptian details as its own | Done | `visibility.clean_office`, `context.visibleOffices` / `whatsappContacts` | e2e offices + WhatsApp test | Owner: Qatar data |
| 1.1 | Hide unconfirmed hours/addresses/facts | Done | `OfficeCard.tsx`, `Footer.tsx`, `clean_office` | `test_bootstrap…` (blanked), e2e | – |
| 1.2 | Typographic image-free tiles | Done | `components/Cards.tsx`, `styles.css` (`.tile--type`) | e2e home/projects; screenshots | – |
| 1.2 | Country/type filtering | Done (already) + hidden when one option | `pages/Projects.tsx`, `Home.tsx` | e2e filter test | – |
| 1.2 | Project search | Done (shown when more than 6 projects) | `pages/Projects.tsx` | e2e search (guarded by count) | – |
| 1.2 | Graceful empty states | Done | `Projects.tsx` ("portfolio being prepared"), `Home.tsx` (section hidden) | build + manual | – |
| 1.3 | Form validation, accessible errors, phone/country, loading/success/error, consent, keyboard | Done (most already existed; reviewed) | `components/EnquiryForm.tsx` | e2e contact tests | – |
| 1.3 | Duplicate-submission protection | Done | client: button disabled while sending; server: content fingerprint, 30 min window | `test_enquiry_bot_timing_and_duplicates`, e2e "stored exactly once" | – |
| 1.3 | Spam protection | Done | honeypot + minimum fill time + IP rate limit | same test | – |
| 1.4 | E-mail notification (SMTP, env-configured) | Done / Configured | `app/notify.py`, `config.py`, `routers/public.py`, `admin.py` (resend), `admin_system.py` (test e-mail) | fake-transport tests + real SMTP round trip (`aiosmtpd`) | **Configured:** company SMTP credentials and `NOTIFY_TO` |
| 1.4 | Delivery status, failures don't lose enquiries, no duplicates, retries | Done | `Enquiry.notify_*` columns, atomic claim, retry loop (10 min, 5 attempts), stale "sending" recovery, admin Retry button | `test_notifications_sent_once_failures_kept_and_retried` | – |
| 1.5 | WhatsApp country routing, context message, unavailable numbers, click tracking | Done | `components/WhatsApp.tsx`, `lib/context.tsx`, ProjectDetail/ServiceDetail set context | e2e WhatsApp test | Owner: Qatar number (if different) |
| 1.6 | Security hardening | Done | `security.py`, `main.py`, `routers/admin*.py`, Dockerfile, compose | see `SECURITY_REVIEW.md` | – |
| 1.7 | Deployment: Dockerfile, compose, Caddy/HTTPS, health checks, restart, logs, caching, fresh index.html | Done / Configured | `Dockerfile`, `docker-compose.yml`, `deploy/Caddyfile`, `.env.example`, `main.py` (`index_template`) | container smoke test; `test_seo_head_status_and_fresh_index` | **Configured:** server, domain, DNS (owner) |
| 2.1 | Visitor journey: service → related work (by recorded scope) → contextual consultation / WhatsApp | Done | `ServiceDetail.tsx`, `ProjectDetail.tsx`, `EnquiryForm.tsx` (`?about=&ref=`) | e2e project CTA test | – |
| 2.2 | Lightbox, zoom, keyboard/swipe, focus return | Done | `components/Lightbox.tsx` | e2e lightbox test | – |
| 2.2 | Previous/next project, related, consultation CTA, mobile gallery | Done | `ProjectDetail.tsx`, `routers/public.project_payload` | `test_text_only_project_is_valid_and_has_prev_next`; e2e | – |
| 2.3 | Privacy-conscious analytics + event spec + admin view | Done | `lib/analytics.ts`, `/api/events`, `AnalyticsDaily`, admin "Status & analytics" | `test_events_are_anonymous_counters` | Event spec: §Analytics below |
| 2.4 | SEO: titles, descriptions, canonical, hreflang, OG, JSON-LD, sitemap, robots, 404, crawler-visible metadata | Done | `app/seo.py`, `main.py` | `test_seo_head_status_and_fresh_index`; e2e head check | – |
| 2.5 | Performance (measured) | Done | dead CSS removed, unused font dependency removed, route splitting kept | `e2e/perf.spec.ts` budgets (CLS < 0.1, JS < 120 kB) | Field measurement after launch |
| 2.6 | Scheduled verified backups, retention, off-server, logging, restore | Done / Configured | `tools/backup.py`, `tools/restore.py`, compose `backup` service, pre-migration backup | `test_backup.py` (2 tests); container run | **Configured:** off-server destination + first restore test |
| 2.7 | Monitoring: health, errors, failed notifications, backups, crashes | Done / Configured | `/api/health/ready` (GET/HEAD), `app/alerts.py`, Docker HEALTHCHECK, log rotation | `test_ready_health`, `test_head_requests…`, container `healthy` | **Configured:** uptime-monitor account, optional webhook |
| 3.1 | Roles admin/editor/viewer enforced on backend; user management | Done | `security.require_role`, `routers/admin_system.py`, `admin/SystemAdmin.tsx` | `test_roles_are_enforced_on_the_server`, `test_every_admin_endpoint_requires_auth` | – |
| 3.2 | Draft preview, publishing controls, completeness, validation, ordering, filtering, save feedback, safe delete | Done | `admin.py` (preview, `projects-order`, completeness), `admin/ProjectsAdmin.tsx`, `admin/ProjectPreview.tsx` | `test_draft_preview_and_reorder`; e2e admin flow | – |
| 3.3 | Media workflow kept (multi-upload, cover, WebP, captions, render labels, order) | Done (unchanged) | `images.py`, ProjectsAdmin | existing tests | Deferred: images themselves |
| 3.4 | Arabic UI audit fixes | Done | area-unit position, menu logo contrast, fallback markup, RTL arrows/lightbox, letter-spacing | AR screenshots; e2e AR pages | Editorial translations: `DEFERRED_CONTENT.md` |
| 3.5 | CSS / codebase cleanup | Done | `styles.css` (174 dead rules removed, 69 → 55 kB of source), dead components removed, `@fontsource/poppins` removed, ruff config | build + e2e regression | Further token consolidation is optional |
| 3.6 | Proof features: profile PDF, testimonials (approval-gated) | Done (hidden until content) | `SiteDocument`, `Testimonial`, `admin_system.py`, `Footer.tsx`, `Testimonials.tsx` | `test_profile_document_and_testimonials_publish_rules` | Owner: PDF, approved quotes. Case metrics and certificates go in project "Details" |
| 4 | Automated QA | Done | 34 backend tests, 49 e2e tests, CI workflow | `QA_TEST_REPORT.md` | CI not yet run on GitHub |
| – | Dependency vulnerability (react-router) | Done | `frontend/package.json` (react-router-dom 7.18.4) | `npm audit` 0 | – |
| – | Images | **Deferred by owner** | – | – | – |

## Database changes (all additive; safe on existing data)
- **`users`:** `role` (existing users become `admin`) and `token_version`.
- **`enquiries`:** `notify_status` (existing rows become `legacy`, so no e-mail storm for old enquiries), `notify_attempts`, `notify_error`, `notified_at`, `fingerprint`.
- **New tables:** `analytics_daily`, `testimonials`, `site_documents`.
- **Migration:** applied automatically at startup by `ensure_columns()`, which first writes `redecor.db.pre-migrate-<timestamp>.bak`. It was verified on an older local database: all 7 columns were added and the rows were kept.
- **Rollback:** stop the app, restore the `.bak` file (or a backup zip), and check out the previous commit.

## Analytics event specification
All events are anonymous counters per day, path and language. No cookies and no personal data.

| Event | When it is counted | Business question |
|---|---|---|
| `page_view` | Every public page view (route change) | Overall traffic, language split |
| `project_view` | A project page loaded | Which projects interest visitors |
| `service_view` | A service page loaded | Demand per service |
| `cta_click` | "Request a consultation" / "Ask about this project" clicked | Intent before the form |
| `enquiry_submit` / `enquiry_success` | Form sent / accepted | Form conversion and drop-off |
| `whatsapp_open` / `whatsapp_click` | WhatsApp button pressed / chat opened | WhatsApp conversion |
| `profile_download` | Company profile PDF downloaded | Interest in the profile |
| `language_switch` / `theme_switch` | Toggles used | Usage of AR and the light theme |

**Conversion rates:**
- Enquiry conversion = `enquiry_success / page_view`.
- WhatsApp conversion = `whatsapp_click / page_view`.

The numbers are shown in /admin → Status & analytics for 7, 30, 90 or 365 days. Visitors who send Do-Not-Track/GPC are not counted.

## Commits in this programme
`git log --oneline 8beba28..HEAD` lists every change. The main groups are:
1. Audit
2. Backend hardening
3. Frontend and admin features
4. End-to-end suite
5. Arabic and empty states, lint and CI
6. Real SMTP test
7. Documentation
