# Content guide: photos, approvals, readiness

This guide is for whoever loads content into the admin (`/admin`). Nothing here changes the
domain, e-mail or hosting.

## 1. Photo file naming (bulk upload)

Name every file like this:

```
<project-slug>__<nn>__<render|executed>[__cover].<jpg|jpeg|png|webp>
```

| Part | Meaning | Example |
|---|---|---|
| `project-slug` | The project's slug exactly as shown in the admin (lowercase, hyphens) | `villa-zamalek` |
| `nn` | Order in the gallery, 1–3 digits | `01`, `02`, `12` |
| `render` / `executed` | **Mandatory.** `render` = design visualization, `executed` = photo of the finished work | `executed` |
| `__cover` | Optional: this photo becomes the project cover | `__cover` |

Examples: `villa-zamalek__01__executed__cover.jpg`, `villa-zamalek__02__render.png`.
The separators are **two** underscores. Files that do not follow the pattern are rejected in the
dry run (unless the CSV below lists them).

### Optional CSV mapping

When renaming files is not practical, add a CSV (UTF-8, with or without BOM; Excel's
"CSV UTF-8" is fine). The admin page offers a template download.

```
filename,project_slug,order,kind,is_cover,alt_en,alt_ar
IMG_0412.jpg,villa-zamalek,1,executed,yes,Living room looking to the garden,
```

A row in the CSV overrides the file name. `kind` must be `render` or `executed`; there is no
default. `is_cover` accepts `yes/true/1`.

### Two ways to run it

* **Admin → Bulk photo upload.** Choose photos or a `.zip`, optionally the CSV, press
  **1. Dry run**. The table shows, for every file, the project it matched, order, kind, cover,
  quality result and action (create / skip-duplicate / reject). Nothing is saved. Press
  **2. Confirm** to add the `create` rows. The database is backed up automatically first, and the
  run is written to the import log.
* **Command line** (on the server):
  `python tools/bulk_images.py --dir <folder> [--mapping map.csv]` prints the dry run;
  add `--apply --as <your admin e-mail>` to really add them (backup first, verified non-empty).

Re-running the same files is safe: identical files (same SHA-256) are skipped.

## 2. Photo quality rules

Checked on every upload (single, bulk and CLI), from the file contents, not the extension:

| Rule | Default | Setting |
|---|---|---|
| Long edge, gallery photo | ≥ 1600 px | `IMAGE_MIN_LONG_EDGE` |
| Long edge, cover | ≥ 2400 px | `IMAGE_MIN_COVER_LONG_EDGE` |
| Aspect ratio (width ÷ height) | 0.5 – 2.4 | `IMAGE_ASPECT_MIN`, `IMAGE_ASPECT_MAX` |
| File size / type | JPEG, PNG, WebP; upload size limit of the server | – |

* Camera rotation (EXIF orientation) is applied, then **all EXIF/GPS metadata is removed** from
  the published versions.
* A photo below the standard can still be accepted with **"Accept below-standard photos"**.
  The admin records who accepted it and when, and the warning stays visible on the photo.

## 3. Render or Executed label

Every project photo must be labelled **Render** or **Executed** before the project can be
published. A photo without a label is never shown on the public site. Renders get a discreet
label on the public site (dictionary keys `projects.render` and `projects.renderShort`).

Existing photos that were already marked as renders were labelled `render` by migration 0002;
nothing was guessed as `executed`.

## 4. Focal point and alt text

In the project editor, click the photo at the point that must stay visible when cards and covers
crop it (e.g. the chandelier, not the ceiling). The site uses it as `object-position`.
Fill the alt text (EN and AR) for every photo: it is read by screen readers and search engines.

## 5. Approvals register (publication gate)

The public site shows:

* a **project** only when its newest *Client permission to publish* record is **approved**;
* a **client logo** only when its newest *Logo usage permission* record is **approved**.

Records are added from the project editor (Approvals panel) or the Clients page. They are never
edited or deleted: a change of status (pending, approved, rejected, revoked) adds a new line with
who gave it, the date, how it was given, and an optional evidence file (stored privately,
downloadable by editors only, every download logged). Deleting a project or client appends a
"revoked" line automatically.

`ENFORCE_APPROVALS=1` is the default and is mandatory in production (`tools/check_env.py` and the
server refuse `0`). Before switching it on for an existing site, run
`python tools/approval_gate_report.py` to see the list of items it will hide.

## 6. Readiness dashboard

**Admin → Readiness** lists every project with: title and description in AR/EN, cover, number of
photos, all photos labelled, alt text EN/AR, approval, published, and **Ready**. Filter
"not ready", sort by the number of missing items, and export to CSV or XLSX for follow-up.

## 7. Importing projects from Excel / CSV / the portfolio manifest

**Admin → Import projects** (or `python tools/import_projects.py --file <file>` on the server).

1. Download the **Excel template**. The *Projects* sheet has the columns; the *Instructions* sheet
   says what goes in each one and which are required (`title_en`, `country`, `type`). Dropdowns
   limit `country`, `type`, `is_render` and `featured` to allowed values.
2. One project per row. Leave a cell empty when the information is not confirmed: never guess.
3. Upload the `.xlsx`, a `.csv` saved as **CSV UTF-8** (with or without BOM, Arabic is kept), or
   the JSON manifest (`tools/portfolio_manifest.json`; extra keys such as `pdf` and `pages` are
   ignored and reported).
4. **Dry run** lists every row with its action (create / update / skip / error) and every bad
   cell as `column: problem`. Nothing is saved.
5. **Confirm** imports the valid rows. Rows with errors are left out.

Rules:

* New projects are always **drafts**. Publish them from the project editor after review, photos
  and the client's permission (Approvals).
* A row whose slug already exists is **skipped**, unless "Update existing projects" is ticked
  (CLI: `--update-existing`). Then only the filled cells change; empty cells keep the current
  values and the published status is never changed.
* Before anything is written the database is backed up (admin page: SQLite copy next to the
  database or in `BACKUP_DIR`; CLI: full `tools/backup.py` archive). Each import is written to the
  import log (who, when, file, counts, backup file) and every created/updated project to the
  audit log.

CLI: `python tools/import_projects.py --file projects.xlsx` (dry run),
`... --apply --as <your admin e-mail>` (import), `--template out.xlsx` (write the template).
