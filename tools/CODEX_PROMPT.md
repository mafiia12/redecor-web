# Prompt for Codex: collect portfolio data and the best renders for the website

Run Codex inside `D:\Master Web (Redecor)` (portfolio PDFs/PPTX + the `redecor-web/` repo). Phase B also needs read access to the company file server. Paste everything below the line.

---

You are preparing content for the RE DECOR & MORE website (offices in Egypt and Qatar; projects in Egypt, Qatar and Saudi Arabia). Collect the data and the best project images, and package them so the website's importer can upload them.

## Hard rules
- **Read-only on all sources.** Never modify, move, rename or delete an original file (local or on the server). Write only inside `D:\Master Web (Redecor)\portfolio_export\`.
- Do not upload anything anywhere and do not push to git.
- **Confidential material stays out.** Never copy contracts, quotations/prices, BOQs, payment or accounting files, personal IDs, staff data, or anything marked confidential. If a project folder contains them, ignore those files and mention only that they exist.
- Never invent facts. A missing value is `null` plus an entry in `needs_confirmation`. Years: only if explicitly stated ("2025-2026" on covers is the portfolio year, file dates are only hints, never use them as the project year).
- Keep original spelling from title pages; flag variants (Sokkar/Sukkar, Ocean's/Oceans, Zahraa/Zahra).

## Phase A: local portfolio files
Sources (match by keyword; names have typos): Fit-out projects PDF + "Fit-out Projects dd" PPTX (executed works), Retail & Commercial PDF (design renders), Residential Egypt PDF, Residential Gulf PDF, OCEAN'S BREEZE PDF, Portfolio brief PDF and "design portfollio" PPTX (company profile, team, stats, clients, more design projects).
1. Re-extract text of every page/slide yourself and classify each page: project | divider | company info | clients | contact | blank.
2. Build one record per project, merged across files (Sokkar Mecca = head-office façade design + Port Said branch renovation).
3. Read `redecor-web/tools/portfolio_manifest.json` (59 entries, some are `draft`) and `redecor-web/tools/import_portfolio.py` to see the schema and the current page ranges.

## Phase B: the company server (best renders and photos)
Locate the project folders on the server (ask me for the path if you cannot find it; mapped drive or UNC path). For every project in the owner's priority list below and for every other project in the manifest:
1. Find the **final, highest-quality images**: final renders (3ds Max/V-Ray/Corona/Lumion/D5/Enscape outputs, "Final", "Render", "Output", "Post", "Presentation" folders), Photoshop post-production exports, and for executed fit-out works the best *finished-space* photos (site-progress photos only if nothing else exists, and flag them).
2. Accept `.jpg .jpeg .png .tif .tiff` (and `.exr/.psd` only to report that they exist). Ignore `.max .skp .dwg .rvt .3ds` and any working files, drafts, "WIP", "test", "old", "backup", clay/AO/mask/z-depth passes, thumbnails, and anything below 1600 px on the long side unless it is the only image.
3. De-duplicate (same picture at several sizes or formats: keep the largest; compare perceptual hashes). Prefer wide interior/exterior hero views first, then details.
4. Export at most **16 images per project** to `portfolio_export/images/<slug>/NN.jpg` (sRGB JPEG, quality 85-90, longest side max 2400 px, metadata stripped; convert TIFF/PNG, flatten transparency onto white). Name files in display order: `01.jpg` = cover candidate.
5. Write `portfolio_export/images/<slug>/images.json`: a list of `{file, source_path, source_modified, width, height, is_render, role (cover|gallery|plan|board), caption_en}`. `is_render` is true for 3D visualizations, false for photographs of built work. `caption_en` is optional, neutral and short ("Dining area with timber ceiling"), no invented brand names.
6. Flag problems in `needs_confirmation`: third-party logos or brand screens visible inside renders (e.g. a streaming logo on a TV), watermarks, misspelled signage, low resolution, client names visible that may need permission.
7. If a project's server folder has several versions (option A/B, before/after), export the approved/final one and list the others in the report.

## Owner's priority list (handwritten note): handle these first
- Hospitality / F&B: Ocean Breeze (the note says "no presentation, execution only": check whether the material is design renders or executed photos), Zahraa Square (Fifth Square), Seven Fortunes (3 branches: Marassi, Walk of Cairo, North Lane; also check Palm Hills and "The Golf" design versions), Park St Mall (a clothing shop; is it "Be Babel, Park St."?), National Bank of Egypt / NBE (Ahli Bank), Dunk.
- Commercial / head-quarters / offices: YK Mall (note: only a moodboard, no design yet: do NOT export it as a project, only report), Downtown Hotel (note has "?!!": find out what it is), El Kasrawy HQ, i Score Hub, Sokkar/Sukkar Mecca (Port Said + head office = one project), Systel, Shorosh, Zayed Mall (same as "Zayed Administrative Building"?).
- Residential: Badya Palm Hills, Ali House (the owner's own house), Bet El Watan (the note says "no presentation": report anything found), plus the residential portfolios (Egypt, Gulf).
- Side note on the sheet: "we work technical drawings only": report which projects are drawings-only. They must never be shown as executed work.
These get `priority: true` and the lowest `sort_order` values, in this order.

## Other data to collect
- `clients/NN-name.png`: every client/partner logo from the "OUR CLIENTS" slides/pages (transparent background when on a white circle/box) + `clients.json` (`name`, `source`, linked projects). Known so far (verify): National Bank of Egypt, Seven Fortunes Coffee Roasters, Tanmeyah, Kasrawy Group, i Score, Fertiglobe, Be Babel, Banque Misr, Sokkar Mecca, Chai Jmr, Systel, Andalusia Hospitals, Modad Properties, Sheraton, ADNOC, ADD Properties. Also check the server for a client-logo folder with originals (prefer vector/PNG originals).
- `company.json`: only stated facts, each with `source`: names, taglines, about, vision, mission, goals, services, process steps (Planning & Budgeting / Design & Development / Execution & Close-Out; the "Plan/Design/Deliver" variant), numbers (30+ projects, 15+ collaborations, 3 regional bases; "EST 2012" next to PROTECH: flag the meaning as unconfirmed), team (name + title: layout is ambiguous, give raw text, best reading and confidence), contacts.

## Deliverables (all inside `portfolio_export/`)
1. `images/<slug>/...` + `images.json` per project (as above).
2. `portfolio_manifest.suggested.json`: same schema as the current manifest (`slug, title_en, pdf | sources, pages, country, type, city_en, scope_en, is_render, featured, summary_en, sort_order, confirm, draft`). Types: residential | hospitality | retail | office | industrial | healthcare | public | education | landscape. Country: eg | qa | sa. Projects whose images come from the server need no `pdf`/`pages`: the importer picks up `images/<slug>/` automatically. Set `draft: true` only when there are no images at all. Do not edit the existing manifest.
3. `manifest_diff.md`: per project: missing projects, wrong page ranges, wrong country/type, duplicates, better sources found on the server.
4. `contact_sheet.html`: every project with its exported images (small thumbnails), source and flags, for quick human review.
5. `REPORT.md`: counts (projects, images, clients, GB read), a table (slug, country, type, render/executed, image count, source, confidence, priority), open questions grouped by who must answer (owner / design team / client permissions), suspicious items (low-res, third-party logos on screens, misspellings, claims like "authorized distributor" that need proof), and the list of server folders you could not access.
6. `clients/`, `clients.json`, `company.json`.

## How the result will be used (do not run it)
```
python tools/import_portfolio.py --pdf-dir "D:\Master Web (Redecor)" --images-dir "D:\Master Web (Redecor)\portfolio_export\images" --manifest "D:\Master Web (Redecor)\portfolio_export\portfolio_manifest.suggested.json" --dry-run
```
So image folder names must equal the manifest `slug`, and the first image (or `role: cover`) is the project cover.

## Working method
Work one project at a time, log progress to `portfolio_export/progress.log`, resume safely if interrupted, stream large files (do not load everything in memory), and prefer being conservative. Python is fine (pymupdf, python-pptx, Pillow, numpy, imagehash). When finished, print the path of `REPORT.md` and a 10-line summary.
