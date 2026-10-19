# Prompt for Codex: run it on the company server and copy the best project images to D:

How to use: connect to the company server (or open the mapped drive), open Codex in the **root project folder on the server**, and paste everything below the line. Codex only reads the server and writes to `D:\Redecor_Export\`.

---

You are helping prepare the website of RE DECOR & MORE (interior design and fit-out contractor: offices in Egypt and Qatar, projects in Egypt, Qatar and Saudi Arabia). This folder is the company file server. Your job: find the best FINAL images of our projects and copy web-ready versions to `D:\Redecor_Export\`.

## Safety rules (non-negotiable)
1. **The server is READ-ONLY for you.** Never write, rename, move, delete or open-for-edit any file under this folder. Copying out is the only allowed operation. No git operations, no uploading anywhere, no network calls.
2. Write only inside `D:\Redecor_Export\`. Check free space on D: first. If free space is below 20 GB, say so and stop before copying.
3. **Never copy confidential material**: contracts, quotations, prices, BOQs, payment/accounting files, IDs, HR files, passwords, anything named like `contract`, `quotation`, `BOQ`, `invoice`, `payment`, `salary`, `confidential`. Do not open or summarize them either; just count them.
4. Never invent facts. Unknown = `null` + a question in the report. Years only if explicitly written in a document; file dates are hints only.

## Phase 1: inventory (do this first, then STOP and show me the summary)
1. Walk the folder tree (skip system/hidden/recycle folders). Log to `D:\Redecor_Export\inventory.csv`: path, type, size, modified date, width and height for images.
2. Detect the project folders: typically one folder per project/client (names may be Arabic or English, with typos). Print a table: folder path, guessed project name, number of images, number of 3D/CAD files (`.max .skp .dwg .rvt`), total size, newest modification date.
3. Match each folder to the project list below (fuzzy match on name, Arabic and English; e.g. "Kasrawy"/"الكسراوي", "Sokkar"/"سكر مكه", "Ahli"/"NBE"/"البنك الأهلي"). Mark: matched / ambiguous / unmatched. List unmatched folders that look like real projects.
4. Report anything that looks like a "final renders", "presentation", "site photos", "handover" or "portfolio" folder per project.
5. Print the summary and **wait for my confirmation** before Phase 2. Do not copy any image before I confirm.

## Phase 2: select and export (after my confirmation)
For every matched project (priority order below):
1. Candidate images: `.jpg .jpeg .png .tif .tiff` (and report `.psd .exr` without exporting). Prefer folders called Final, Render(s), Output, Post, Presentation, Photos, Handover, صور, نهائي, ريندر.
2. Exclude: drafts, WIP, test, old, backup, "copy", thumbnails, clay/AO/mask/z-depth/alpha passes, sketches, screenshots of CAD, scans of documents, images below 1600 px on the long side (unless it is the only image), anything inside confidential folders.
3. De-duplicate with perceptual hashing (same picture at several sizes/formats: keep the largest).
4. Pick at most **16 images per project**: cover first (best wide hero view of the main space or façade), then varied views (different rooms/angles), details last. For executed projects prefer finished-space photos; progress photos only if nothing else exists, and flag them.
5. Convert each chosen image to sRGB JPEG, quality 90, longest side max 2400 px, metadata stripped, flatten transparency on white. Save as `D:\Redecor_Export\images\<slug>\01.jpg`, `02.jpg`, ... (`01` = cover).
6. Write `D:\Redecor_Export\images\<slug>\images.json`: a list of `{file, source_path, source_modified, width, height, is_render, role, caption_en}`. `is_render` = true for 3D visualizations, false for photographs of built work. `role` = cover | gallery | plan | board. `caption_en` optional, short, neutral (e.g. "Dining area with timber ceiling"); do not guess brand names.
7. Optional, only if free space on D: is more than 3x the estimated size: for the top 10 priority projects also copy the ORIGINAL chosen files to `D:\Redecor_Export\originals\<slug>\` (plain copy, same names). Otherwise just record their source paths.
8. Flag in `needs_confirmation`: third-party logos or branded screens visible inside renders, watermarks, misspelled signage, client names or faces visible, low resolution, several versions (A/B options, before/after: export the approved/final one and list the others).

## Phase 3: reports
In `D:\Redecor_Export\` create:
- `REPORT.md`: counts (folders scanned, images considered, exported, GB read), a table per project (slug, server folder, images exported, renders vs photos, confidence, open questions), unmatched folders that look like real projects (candidates for new projects), projects with no usable images, suspicious items, and folders you could not access.
- `contact_sheet.html`: every project with small thumbnails of its exported images plus the source path and flags, for human review.
- `new_projects_found.json`: any real project folder that is not in the list below: `{suggested_slug, title_guess, folder, image_count, notes}`.
- `progress.log`, updated continuously. If interrupted, resume from the log without re-copying finished projects.

## Project list (slug = folder name to use in `images\`)
Use these slugs exactly. Priority = the first rows (the owner's most important projects, in this order); `draft` rows have no known material yet, so search for them by name on the server.

| # | slug | title | country | type | kind |
|---|------|-------|---------|------|------|
| 1 | `oceans-breeze` | Ocean’s Breeze | eg | hospitality | render |
| 2 | `zahraa-al-maadi-fifth-square` | Zahraa Al Maadi, Fifth Square | eg | landscape | executed |
| 3 | `seven-fortunes-marassi` | Seven Fortunes, Marassi | eg | hospitality | executed |
| 4 | `seven-fortunes-walk-of-cairo` | Seven Fortunes, Walk of Cairo | eg | hospitality | executed |
| 5 | `seven-fortunes-north-lane` | Seven Fortunes, North Lane | eg | hospitality | executed |
| 6 | `national-bank-of-egypt-ithad-al-shorta` | National Bank of Egypt, Ithad Al Shorta | eg | office | executed |
| 7 | `kasrawy-group-factory-head-office` | Kasrawy Group Factory Head Office | eg | office | executed |
| 8 | `i-score-hub` | i Score Hub | eg | office | executed |
| 9 | `sokkar-mecca` | Sokkar Mecca | eg | retail | executed |
| 10 | `systel-head-office` | Systel Head Office | eg | office | render |
| 11 | `shorosh` | Shorosh | eg | retail | executed |
| 12 | `sheraton-cairo-hotel-casino` | Sheraton Cairo Hotel & Casino | eg | hospitality | executed |
| 13 | `redecor-head-office` | Redecor Head Office | eg | office | executed |
| 14 | `mohandessin-apartment` | Mohandessin Apartment | eg | residential | executed |
| 15 | `neo-classic-apartment` | Neo Classic Apartment | eg | residential | executed |
| 16 | `tanmeyah-imbaba-mazghouna` | Tanmeyah, Imbaba & Mazghouna Branch | eg | office | executed |
| 17 | `be-babel` | Be Babel | eg | hospitality | executed |
| 18 | `chai-jmr-mamsha-ahl-masr` | Chai Jmr, Mamsha Ahl Masr | eg | hospitality | executed |
| 19 | `al-kbous-factory` | Al-Kbous Factory | eg | industrial | executed |
| 20 | `october-dry-port` | October Dry Port | eg | industrial | executed |
| 21 | `metropolitan-school` | Metropolitan School | eg | education | executed |
| 22 | `vapsera` | Vapsera | eg | retail | executed |
| 23 | `ismailia-stadium` | Ismailia Stadium | eg | public | executed |
| 24 | `el-salam-hospital` | El Salam Hospital | eg | healthcare | executed |
| 25 | `villa-mountain-view` | Villa, Mountain View | eg | residential | render |
| 26 | `villa-new-capital` | Villa, New Capital | eg | residential | render |
| 27 | `residential-interiors-egypt` | Residential Interiors, Egypt | eg | residential | render |
| 28 | `residential-apartments-qatar` | Residential Apartments, Qatar | qa | residential | render |
| 29 | `fertiglobe-meeting-room` | Fertiglobe, Meeting Room | eg | office | render |
| 30 | `fertiglobe-technology-room` | Fertiglobe, Technology Room | eg | office | render |
| 31 | `zayed-administrative-building` | Zayed Administrative Building | eg | office | render |
| 32 | `seven-fortunes-palm-hills-design` | Seven Fortunes, Palm Hills: Design | eg | hospitality | render |
| 33 | `seven-fortunes-marassi-design` | Seven Fortunes, Marassi: Design | eg | hospitality | render |
| 34 | `chai-jmr-el-alamein` | Chai Jmr, Marina El Alamein | eg | hospitality | render |
| 35 | `chai-jmr-abha` | Chai Jmr, Abha | sa | hospitality | render |
| 36 | `jumanji-board-games-jeddah` | Jumanji Board Games | sa | retail | render |
| 37 | `andalusia-hospitals-jeddah` | Andalusia Hospitals | sa | healthcare | render |
| 38 | `amanda-hair-salon-doha` | Amanda Hair Salon | qa | retail | render |
| 39 | `the-shield` | The Shield | eg | office | render |
| 40 | `global-exchange` | Global Exchange | eg | office | render |
| 41 | `m-bag-tower` | M-BAG Tower | eg | office | render |
| 42 | `urban-cafe-strip` | Urban Café Strip | eg | hospitality | render |
| 43 | `courtyard-villa` | Courtyard Villa | eg | residential | render |
| 44 | `beans-cafe` | Beans Café | eg | hospitality | render |
| 45 | `steak-and-stone` | Steak & Stone | eg | hospitality | render |
| 46 | `cafe-wonder` | Café Wonder | eg | hospitality | render |
| 47 | `skadi` | Skadi | eg | retail | render |
| 48 | `royal-palace-hotel` | Royal Palace Hotel | eg | hospitality | render |
| 49 | `hayah-training-center` | Hayah Training Center | eg | education | render |
| 50 | `executive-residence` | Executive Residence | eg | residential | render |
| 51 | `grand-residence` | Grand Residence | eg | residential | render |
| 52 | `noir-residence` | Noir Residence | eg | residential | render |
| 53 | `dunk` | Dunk | eg | hospitality | executed (draft) |
| 54 | `park-street-mall` | Park Street Mall (clothing shop) | eg | retail | executed (draft) |
| 55 | `downtown-hotel` | Downtown Hotel | eg | hospitality | executed (draft) |
| 56 | `zayed-mall` | Zayed Mall | eg | retail | executed (draft) |
| 57 | `badya-palm-hills` | Badya Palm Hills | eg | residential | executed (draft) |
| 58 | `ali-house` | Ali House | eg | residential | executed (draft) |
| 59 | `bet-el-watan` | Bet El Watan | eg | residential | executed (draft) |

Owner's notes (handwritten): Ocean Breeze is "execution only / no presentation" (check whether the material is design renders or executed photos); YK Mall has only a moodboard, no design yet: do NOT export it as a project, just report it; "Downtown Hotel" has a "?!!" (find out what it is); Park St Mall = a clothing shop (is it "Be Babel, Park St."?); Zayed Mall (same as Zayed Administrative Building?); residential Badya Palm Hills, Ali House (the owner's own house) and Bet El Watan have no presentation yet; "we work technical drawings only" marks drawings-only projects, which must never be shown as executed work (report which ones).

## Method
Work one project at a time, stream files (never load a whole folder in memory), log everything, and be conservative: a missing image is better than a wrong or confidential one. Python is fine (Pillow, numpy, imagehash, pandas). Install missing packages with pip. When Phase 1 or Phase 3 finishes, print the path of the report and a 10-line summary.
