# RE DECOR & MORE: website and admin application, full project report

> **Update 2026-10-18: hardening and launch-readiness programme completed.** Sections 1–8 below are the original
> baseline, kept for history. The verified current state is in **§11**. Details are in `IMPLEMENTATION_REPORT.md`,
> `SECURITY_REVIEW.md`, `QA_TEST_REPORT.md`, `DEPLOYMENT_GUIDE.md`, `BACKUP_AND_RECOVERY.md`, `LAUNCH_READINESS.md` and
> `DEFERRED_CONTENT.md`.

> **Prompt to paste into ChatGPT together with this file**
>
> أنت مستشار تقني وخبير UX لمواقع شركات التصميم الداخلي والمقاولات. اقرأ التقرير المرفق عن موقع شركة RE DECOR & MORE (الكود الحالي، القرارات اللي اتاخدت، والنواقص). عايز منك:
> 1. تقييم صريح للوضع الحالي (المنتج، تجربة المستخدم، التقنية).
> 2. خطة تطوير مرتبة بالأولوية (Now / Next / Later) مع سبب كل بند وأثره المتوقع على العملاء المحتملين.
> 3. اقتراحات محددة لتحسين تجربة الزائر (الوصول للمشاريع، الثقة، طلب الاستشارة، الواتساب، النسخة العربية).
> 4. أي مخاطر تقنية أو أمنية قبل النشر على الإنترنت.
> التزم بالقيود المذكورة في القسم 9 (ممنوع اختراع بيانات أو أرقام أو عملاء).

---

## 1. Company and goal

- **Company:** RE DECOR & MORE (Redecor Group), an interior design and build contractor. Services are architectural and interior design, fit-out, contracting, procurement and supply, and project management.
- **Markets:** Egypt (main office in Mohandessin, Giza), Qatar, and Saudi Arabia (some projects).
- **Audience:**
  - villa and apartment owners
  - developers
  - hotel, F&B and retail operators
  - corporate offices
- **Site goal:** build trust through the work (portfolio first), then convert visitors into a consultation request or a WhatsApp conversation.
- **Languages:** English at `/`, Arabic (RTL) at `/ar/...`.
- **Visual references the owner chose:**
  - apple.com product pages, the original brief
  - dararafa.com
  - **nuvelti.com**, the current main reference: black, minimal, image-led, dense project mosaic, standalone project pages
- **Status:** feature-complete for a first launch; real project photos are still to come. Projects will be imported from the company server, curated renders included. Hosting and the domain (redecorgroup.com) are postponed.

## 2. Architecture

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite 8, react-router 6, no UI framework, a single hand-written `styles.css` (~2,000 lines) |
| Backend | FastAPI (Python 3.12+), SQLAlchemy 2.x, SQLite by default (PostgreSQL-ready via `DATABASE_URL`) |
| Images | Pillow. Each upload becomes responsive WebP variants (480–2400 px) in `uploads/<key>/<width>.webp`, served with immutable caching. The average colour is stored for placeholders. |
| Auth | Single admin role, JWT (PyJWT) + scrypt password hashing, rate-limited login (8 tries per 5 minutes) |
| Serving | FastAPI serves the API, `/media`, and the built SPA (`frontend/dist`). `index.html` is cached at startup, so restart after each frontend build. Sitemap and robots are generated. The Open Graph image is absolute via `SITE_URL`. |
| Deploy | `Dockerfile` (multi-stage: Node build, then Python runtime), `docker-compose.yml` with a `/data` volume (DB + photos), `.env.example`, and a `DEPLOY.md` guide |
| Data safety | `tools/backup.py` zips the DB and the uploads. `ensure_columns()` adds new DB columns automatically at startup (forward-only, never drops data). The `audit_log` table records every admin write. |

### Repository layout
```
backend/app/
  main.py          app, lifespan (create tables + ensure_columns + seed), SPA serving, sitemap, validation handler
  models.py        User, Image, Project, ProjectImage, Client, SiteImage, Office, Enquiry, AuditLog
  schemas.py       Pydantic in/out models
  routers/public.py   /api/health, /api/bootstrap (ETag), /api/projects/{slug}, POST /api/enquiries
  routers/admin.py    login/me, CRUD projects (+images, +client logo), clients, site-image slots, offices, enquiries
  images.py        upload processing, orphan cleanup
  slots.py         list of named image slots the site uses (home-hero, service-*, how-we-work-1..3, division-*, about-hero, ...)
  seed.py          offices (Egypt real data; Qatar placeholders), admin user from env, optional demo data
backend/tests/     12 pytest tests (API, auth, rate limits, uploads, cache headers, new project fields, 422 handling)
frontend/src/
  pages/           Home, Projects, ProjectDetail, ServiceDetail, About, Contact, Privacy, NotFound
  components/      Header (nav + Projects dropdown by type + language + theme toggle), Footer, WhatsApp FAB (Egypt/Qatar sheet),
                   SectionHead, Divisions, HowWeWork, ClientWall, ProjectStrip, WorkHero, Cards (ProjectTile), EnquiryForm, OfficeCard, Photo
  admin/           Projects, Clients, Site images, Offices, Enquiries (behind login)
  i18n.ts          all EN/AR UI copy + service texts
  content.ts       team (4 people with confirmed titles) and the 4 divisions text
  config.ts        social links, default THEME ("dark")
  lib/             api client + types, contexts (language, data cache in sessionStorage), hooks (reveal, hero scale), theme store
tools/             import_portfolio.py (PDFs or folders of renders -> projects), import_clients.py (logos from PowerPoint),
                   seed_test_projects.py (2 marked TEST projects), backup.py, portfolio_manifest.json (59 projects, 7 drafts),
                   CODEX_PROMPT*.md (prompts to extract renders from the company server)
```

## 3. Public site: current pages and behaviour

1. **Home**
   - Hero: the large company logo, the headline "Spaces, finished to the last detail." anchored at the bottom, the sub-line, and two CTAs (Request a consultation / See our projects). When ≥3 featured projects have covers, a horizontal project strip appears above.
   - 01 Services: 4 numbered index rows (Contracting, Interior Fit-Out, Procurement & Supply, Project Management). Each links to a service page, and a thumbnail appears on hover when a photo is uploaded.
   - 02 Selected work: dense mosaic of featured projects; the title appears on hover (always shown on touch screens); country filter.
   - 03 Divisions: side tabs for Interior Design, Execution & Fit-Out, Contracting & Commercial and Business Development. Each tab has an optional render image, a description, 4 scope points, and the division lead; a leadership row (CEO) sits below.
   - 04 How We Work: 3 fixed steps (Planning & Budgeting, Design & Development, Execution & Close-Out), with optional photos.
   - 05 Clients: borderless logo wall (16 real logos extracted from the company profile). Grayscale; full colour on hover.
   - CTA band ("Planning a project?") and the footer.
2. **Projects:** compact image hero, then text-tab filters (country, type; the type also comes from the header dropdown via `?type=`), a project count and the mosaic. Draft or unpublished projects are hidden.
3. **Project page**, standalone and Nuvelti-style:
   - Layout: black, narrow centred column. Small bold title, then the client logo on a white banner, then a hero image.
   - Text block: tagline, summary, then a facts list (written in the admin as "Label: Value" lines, or auto-built from the fields). After that, a story with `## Heading` sections such as "Design Concept" and "Vision".
   - Gallery: full rows, with consecutive "half" images paired side by side. Captions are small and centred. Render badges appear where relevant.
   - Footer: related projects.
4. **Service page** (4 services): hero, "What's included" list (for fit-out and supply), related projects, CTA.
5. **About:**
   - text supplied by the company
   - stats (30+ projects, 15+ collaborations, "3 regional bases", which is still to be confirmed)
   - vision and mission
   - Divisions and How We Work
   - offices
6. **Contact:**
   - enquiry form (name, phone with country code, email, country, service, project type, area, message, preferred contact method, consent; honeypot + rate limit)
   - beside it, the office blocks with Google Maps links (rows with placeholder values are hidden)
7. **Global:**
   - dark (default) and light theme toggle, saved per visitor
   - full EN/AR with RTL and Arabic typography (IBM Plex Sans Arabic); the type family is Inter
   - WhatsApp floating button (asks Egypt or Qatar), back-to-top button
   - SEO meta per page, sitemap, Open Graph, `prefers-reduced-motion` support, skip link, keyboard-operable tabs

## 4. Admin (`/admin`)
- **Projects:** create and edit all fields in EN/AR:
  - title, city, country, type, year, area, scope, summary
  - tagline, client name, details, story
  - published / featured / render flags, order
  - photo upload (multi), per-photo cover, render flag, layout (full/half), caption EN/AR, order, delete
  - client logo upload
- **Clients:** name, URL, logo, order, publish.
- **Site images:** one upload per named slot (home hero, services, how-we-work steps, divisions, about, projects hero), with alt text EN/AR.
- **Offices:** address, phone, WhatsApp, email, hours, Maps link for Egypt and Qatar.
- **Enquiries:** list and status (new / contacted / closed).

## 5. Development history (what was built, in order)
1. Full-stack build from the company's design system: Apple-style, bilingual, admin, responsive images.
2. Real company content: contacts, socials, About text, the 4 services, address, team titles.
3. Tooling to extract portfolio images from large PDF portfolios and client logos from the PowerPoint profile. Codex prompts to pull the best renders from the company file server.
4. Restyles: first Dar Arafa-inspired, then Nuvelti-inspired (dark, mosaic, dropdown nav).
5. Standalone Nuvelti-style project pages with tagline, story, client logo, per-image layout, and automatic DB migration.
6. "Big update":
   - theme toggle
   - empty image slots render nothing (no grey boxes)
   - tighter spacing
   - Divisions with team
   - project facts list
   - test-data script
   - Docker deployment, backup
7. Agency-style pass, then an independent design review whose fixes were applied:
   - editorial left-aligned hero
   - single type family
   - numbered section headers
   - service index rows
   - fixed 3-step process
   - borderless logo wall
   - full footer
   - contact form beside offices
   - shorter projects hero
   - short render badges

## 6. Known gaps and open items

**Content and data (owner to supply; nothing will be invented):**
- **Real project photos:** none are online yet. The owner will curate renders from the company server, then import them with `tools/import_portfolio.py --images-dir`. Projects are hidden until reviewed.
- **Images for empty site slots:** home hero, service images, how-we-work steps, divisions, about.
- **Qatar office:** address, phone and hours. Both offices currently show the Egyptian number, and Egypt's hours are also missing.
- **About stat:** "3 regional bases" vs. two offices shown; to be confirmed.
- **Project-name questions:**
  - Park St Mall = Be Babel?
  - Downtown Hotel = Sheraton?
  - Zayed Mall = Zayed Administrative Building?
  - Sokkar vs Sukkar spelling
  - The Shield / Global Exchange split
- **Client-logo permission:** Fertiglobe and ADNOC both appear as clients; permission to show the logos is pending.
- **Execution division:** no lead named yet.
- **Marketing copy flagged by the design review as generic:**
  - service taglines such as "Built with precision."
  - the contact headline "Let's Build Something Exceptional."
  - the vision sentence
  - the how-we-work paragraphs

  The company wrote these, so they are kept until the owner approves new wording.

**Product and UX gaps:**
- **New enquiries:** no notification (email, WhatsApp or Telegram). They are only visible in the admin.
- **Tracking:** no analytics or conversion tracking (form submits, WhatsApp clicks, project views).
- **Projects page:** no search, and no pagination or "load more"; this is fine for about 60 projects.
- **Project page:** no image lightbox or zoom, and no previous/next project navigation.
- **Downloads and proof:** no downloadable company profile (PDF), no testimonials, case metrics or certificates; these need real data.
- **Admin workflow:**
  - no bulk reordering by drag and drop
  - no draft preview link
  - a single admin role (no editor or viewer roles)
- **Arabic content:** many project fields will only exist in English at first; the UI falls back to English.

**Technical debt:**
- **`styles.css`:** about 2,000 lines built in several redesign passes, with later override blocks and a few `!important`. It should be consolidated into one token-based stylesheet, or CSS modules.
- **Poppins:** still listed in `package.json` but no longer used. Remove it.
- **Rate limiter:** in memory and single process. Use Redis or a reverse-proxy limit if scaling to several workers.
- **Database:** SQLite is fine for this traffic. Use PostgreSQL if several editors or larger scale.
- **Tests:** no frontend tests (unit, e2e or visual regression); Playwright screenshots were run manually during development.
- **Backups and monitoring:** no CI pipeline yet, and no automated off-server backup or uptime monitoring.
- **Rendering:** client-rendered SPA. SEO is acceptable thanks to the meta tags and sitemap, but pre-rendering or SSR of project pages would improve sharing previews and indexing.

## 7. Roadmap currently planned
- **Now (before launch):**
  - import the real renders and executed-project photos for the priority projects
  - fill the empty image slots
  - fill in the Qatar and Egypt office data
  - confirm the open content questions
  - set `SEED_DEMO=0`, a new `SECRET_KEY` and a strong admin password
  - remove the TEST projects
  - deploy with Docker behind HTTPS (Caddy) on the domain
- **Next:**
  - email or WhatsApp notification for new enquiries
  - analytics with events (consultation submit, WhatsApp click, project view)
  - lightbox and previous/next on project pages
  - CSS consolidation
  - daily automated backup
- **Later:**
  - case-study metrics and testimonials (only with real data)
  - downloadable profile
  - pre-rendered project pages
  - admin roles and drag-and-drop ordering
  - a fully Arabic content pass

## 8. Key UX decisions already taken (and why)
- **Portfolio first, Nuvelti-style:** dark, minimal, image-led. The work sells, so text stays short.
- **Logo prominent on the home page:** an explicit owner request.
- **No empty grey boxes:** a section without a photo collapses gracefully, so the site looks finished before every photo exists.
- **Renders are always labelled:** "Render" / "Design visualization", for honesty with clients.
- **WhatsApp is a primary contact channel:** this is the regional norm. The visitor picks the Egypt or Qatar number.
- **Bilingual with real RTL:** mirrored layout and Arabic type, not just translated strings.
- **Light theme toggle:** available, but dark remains the brand default.

## 9. Constraints for any suggestion
- **Never invent:** prices, client names, statistics, years of experience, awards, testimonials, certificates or project facts. Missing data stays hidden until the company supplies it.
- **Wording:** do not write "authorized distributor" anywhere.
- **Brand name:** keep "Redecor Group" wording as the owner set it.
- **Approvals:** client logos and project photos are shown only with the company's approval. Draft projects stay hidden.
- **Data safety:** no destructive DB or data changes without explicit approval; keep backups.
- **Stack:** keep the current stack (React + FastAPI) unless there is a strong reason; the owner maintains it locally on Windows (VS Code, PowerShell).

## 10. How to run locally (Windows, PowerShell)
```powershell
# backend (terminal 1)
cd backend
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then edit SECRET_KEY / ADMIN_EMAIL / ADMIN_PASSWORD
uvicorn app.main:app --port 8001

# frontend build (terminal 2)
cd frontend
npm install
npm run build            # then restart the backend so it serves the new build

# optional: two TEST projects to preview the layout
pip install -r tools/requirements.txt
python tools/seed_test_projects.py --api http://localhost:8001 --email <admin email>
```
Open http://localhost:8001 for the site and http://localhost:8001/admin for the admin.


## 11. Verified state after the hardening programme (2026-10-18)
- **Content integrity:** one server-side public filter. Drafts, `test-project-*`, `[placeholder]` titles, unapproved or logo-less clients and unapproved testimonials never reach the public site, API or sitemap. Placeholder office values are blanked; the Qatar office is hidden until it has its own address. The unverified "3 regional bases" stat is hidden. Arabic fallbacks are marked `lang="en" dir="ltr"`.
- **Without photos:** typographic project tiles, text-only project pages, and graceful empty states. Images are **deferred by the owner**; the whole media workflow is unchanged and ready.
- **Enquiries:**
  - stored first
  - deduplicated, with a bot timing check
  - e-mail notification via SMTP from the environment, with delivery status, automatic retries and a manual retry
  - tested against a real local SMTP server
  - company credentials pending
- **WhatsApp:** one row per distinct number, a prefilled message carrying the project or service context, and click tracking.
- **Security:**
  - production configuration guard
  - revocable JWT (`iat`/`ver`)
  - password policy and change
  - per-IP and per-account login limits
  - roles admin/editor/viewer enforced on all 43 admin endpoints
  - CSP, HSTS and COOP; body size limits
  - docs off in production
  - non-root container, proxy-safe port binding
  - dependency audits clean
- **SEO:** server-rendered `<head>` per URL (title, description, canonical, hreflang, OG, JSON-LD) and real 404 status. `index.html` is re-read after each build, so no restart is needed.
- **Visitor journey:** lightbox (keyboard, swipe, zoom), previous/next project, project/service-aware consultation CTA.
- **Analytics:** first-party, cookie-free counters with an admin dashboard (event spec in IMPLEMENTATION_REPORT.md).
- **Operations:**
  - Docker + Caddy (HTTPS) + daily verified backup service with retention and off-server copy
  - restore tool
  - pre-migration database copies
  - deep health endpoint (GET/HEAD)
  - optional alert webhook
  - log rotation
- **Admin:**
  - users and roles
  - my account (password)
  - status and analytics, test e-mail
  - documents (company profile PDF)
  - testimonials (approval-gated)
  - draft preview
  - completeness indicator, search/filter, reorder
  - typed delete confirmation
  - enquiry e-mail status and retry
- **Quality:** 34 backend tests, 49 Playwright tests (desktop, tablet, mobile; EN/AR; accessibility; performance budgets), ruff clean, `tsc` clean, CI workflow added (not yet run on GitHub).
- **Launch gate:** **CONDITIONAL GO**. These remain owner actions:
  - server and `.env` secrets
  - SMTP credentials
  - off-server backup destination and a restore test
  - client-logo permission and Divisions wording approval
  - removing the TEST projects
  - publishing real projects
  - DNS
