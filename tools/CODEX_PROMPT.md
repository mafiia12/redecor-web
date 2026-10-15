# Prompt for Codex: extract the portfolio data and image renders

Open Codex in `D:\Master Web (Redecor)` (the folder that holds the portfolio PDFs and PPTX files) and paste everything below the line.

---

You are preparing content for the RE DECOR & MORE website (Egypt, Qatar, Saudi Arabia). In this folder there are portfolio PDFs and PowerPoint files, plus a git repo `redecor-web/`. Your job is to read ALL of the source files and produce a clean, verified data export and web-ready images. **Do not modify, move, rename or delete any original file. Do not upload anything anywhere. Write only inside a new folder `portfolio_export/`.**

## Source files (match by keyword in the file name; names have typos)
- `Redecor Fit-out projects.pdf` and `Redecor Fit-out Projects dd*.pptx`: executed fit-out projects (real site photos)
- `Retial &Commerical Portfolio.pdf`: retail/commercial/office DESIGN projects (3D renders)
- `Resedintial in egypt Portfolio.pdf`, `Resedintial in Gulf Area Portofolio.pdf`: residential DESIGN projects (renders)
- `OCEAN'S BREEZE.pdf`: one restaurant design project (renders, plan, furniture board, material board)
- `Redecor Portfolio breif @Redecor.pdf` (company profile) and `design portfollio.pptx`: company profile, services, team, stats, clients, more design projects
- The text of each file was already extracted once; extract it again yourself, do not rely on memory.

## 1. Projects (most important)
For every project found anywhere (title pages, slide titles, "SOURCE PAGE n" notes in the PPTX, captions), create one record. Merge the same project when it appears in several files (e.g. "Sokkar Mecca" = head-office façade design + Port Said branch renovation). Fields:
`slug` (kebab-case), `title_en`, `client`, `country` (eg | qa | sa, only if the files say so, else `null`), `city` (only if stated), `type` (residential | hospitality | retail | office | industrial | healthcare | public | education | landscape), `scope` (e.g. "Fit-out", "Interior design", "Exterior design", "Renovation"), `is_render` (true for 3D design visualizations, false for photos of executed work), `year` (only if explicitly stated; otherwise `null`; the "2025-2026" on covers is the portfolio year, not a project year), `summary_en` (only text copied or lightly cleaned from the files, never invented), `sources` (`[{file, pages: [first, last]}]`), `image_count`, `confidence` (high | medium | low) and `needs_confirmation` (list of open questions, e.g. country unknown, name ambiguous, page split unclear).
Rules: **never invent** names, dates, areas, clients, cities or statistics. If something is not in the files, use `null` and list it under `needs_confirmation`. Spelling: keep the spelling used on the title page, and flag variants (e.g. Sokkar vs Sukkar).

## 2. Images / renders
For each project export the best images to `portfolio_export/images/<slug>/NN.jpg`:
- Use the embedded original pictures from the PDF/PPTX (not screenshots of pages) whenever possible; fall back to rendering the page only if there is no embedded picture.
- Skip: logos, icons, backgrounds, title-only pages, plan drawings unless the project is a design project that needs them, duplicates and near-duplicates, anything smaller than 1000 px on the short side.
- Max 16 images per project, evenly chosen, cover candidate first (the strongest wide interior/exterior view). Convert to sRGB JPEG, quality 85, longest side max 2400 px, strip metadata.
- Write `portfolio_export/images/<slug>/images.json` with, for each image: file name, source file, page/slide, width, height, `is_render`, `role` (cover | gallery | plan | board), and a one-line neutral `alt_en` description of what is visible (e.g. "Dining area with timber ceiling"; do not guess brand names).
- Also produce `portfolio_export/contact_sheet.html` showing every project with its images and the page numbers so a human can review quickly.

## 3. Clients and partners
Export every client/partner logo from the "OUR CLIENTS" slides/pages to `portfolio_export/clients/NN-name.png` (transparent background when the logo sits on a white circle or white box; keep colours). Write `clients.json` with `name` (as readable on the logo), `source`, and any project they are linked to. Known so far (verify): National Bank of Egypt, Seven Fortunes Coffee Roasters, Tanmeyah, Kasrawy Group, i Score, Fertiglobe, Be Babel, Banque Misr, Sokkar Mecca, Chai Jmr, Systel, Andalusia Hospitals, Modad Properties, Sheraton, ADNOC, ADD Properties. Report any additional ones.

## 4. Company facts
Write `company.json` with only what is stated in the files, each value with its `source`: legal/brand names, tagline(s), about text, vision, mission, goals, services list (design, shop drawings, detailed plans, 3D visualization, BIM, fit-out execution, furnishing, back-office support), process steps ("Planning & Budgeting", "Design & Development", "Execution & Close-Out" and the "Plan / Design / Deliver" variant), numbers ("30+ projects", "15+ collaborations", "3 regional bases", "EST 2012" next to PROTECH: flag the meaning as unconfirmed), team (name + title; the layout is ambiguous, so report the raw text and your best reading with a confidence), contacts (email, phone, address, website, social links).

## 5. Reconcile with the website importer
Read `redecor-web/tools/portfolio_manifest.json` and `redecor-web/tools/import_portfolio.py`. Produce `portfolio_export/manifest_diff.md` listing, project by project: missing projects, wrong page ranges, wrong country/type, duplicates, and images that the current page ranges would miss or wrongly include. Also write `portfolio_export/portfolio_manifest.suggested.json` in exactly the same schema as the existing manifest (`slug, title_en, pdf, pages | sources, country, type, city_en, scope_en, is_render, featured, summary_en, sort_order, confirm`) so it can replace the current one after review. Do not edit the existing manifest.

## 6. Final report
Create `portfolio_export/REPORT.md` with: counts (projects, images, clients), a table of all projects (slug, country, type, render/executed, image count, confidence), the full list of open questions grouped by who must answer (owner / design team / client permissions), and a list of anything suspicious (low-resolution images, third-party watermarks or logos visible on screens, e.g. brand logos on TVs, text in images that is wrong or misspelled, claims such as "authorized distributor" that need proof).

## Working rules
- Be systematic: process one source file at a time, log progress, and keep going until every page/slide has been classified (project page, section divider, company info, clients, contact, blank).
- Python is fine (PyMuPDF `pymupdf`, `python-pptx`, Pillow, numpy). Install packages with pip if needed.
- Large files: stream page by page, do not load everything in memory.
- Prefer being conservative: a missing field is better than a wrong one.
- When finished, print the path of `REPORT.md` and a 10-line summary.
