# Backup and recovery

## 1. What is protected
| Data | Where | In the backup |
|---|---|---|
| Database: projects, clients, offices, enquiries, users, analytics counters | `redecor.db` (SQLite) or PostgreSQL | yes |
| Uploaded photos (all WebP sizes), logos, company profile PDF | `uploads/` | yes |
| Code | GitHub repository | not needed (re-clone) |
| Secrets (`.env`) | server only | **no**: keep a copy in the company password manager |

## 2. How backups are made (`tools/backup.py`)
Each run does five things:
1. **Consistent database copy.** It uses SQLite's online-backup API, which is safe while the site is running. For PostgreSQL it uses `pg_dump`.
2. **Zip.** It packs the database copy with every uploaded file and a `manifest.json` (counts and SHA-256 checksum).
3. **Verification.** It checks the CRC of every zip member, compares the database checksum, runs `PRAGMA integrity_check` and opens the `projects` table. A backup that fails verification is reported as **FAILED**.
4. **Off-server copy (optional).** With `--copy-to` or `BACKUP_COPY_TO` set, the zip is copied to a second location and the copy's checksum is verified.
5. **Retention.** Only the newest `--keep` / `BACKUP_KEEP` backups are kept (default 14), on both sides.

On failure the exit code is non-zero, a `FAILED` line goes to the log, and an alert is sent if `ALERT_WEBHOOK_URL` is set.

Before every automatic schema change, the backend also saves `redecor.db.pre-migrate-<date>.bak` next to the database.

## 3. Schedule
- **Docker:** the `backup` service in `docker-compose.yml` runs once a day (`--loop-hours 24`) into `/data/backups`. `docker compose logs backup` shows the result of each run.
- **Windows (no Docker):** Task Scheduler, daily:
  ```
  Program:  D:\Master Web (Redecor)\redecor-web\backend\.venv\Scripts\python.exe
  Arguments: ..\tools\backup.py --out-dir D:\Backups\redecor --keep 30 --copy-to "\\NAS\Backups\redecor"
  Start in: D:\Master Web (Redecor)\redecor-web\backend
  ```

### Off-server copies (required before launch)
A backup that lives only on the same server is lost together with that server. Choose one option:
- **On the VPS:** mount a storage box or S3 bucket (rclone mount, or the provider's block storage) and set `BACKUP_COPY_TO=/offsite`, uncommenting the volume line in `docker-compose.yml`.
- **Pull to the office:** copy `/data/backups/*.zip` daily to a company NAS or OneDrive, e.g. with `scp` from a scheduled task, or `rclone copy`.

**Status:** the code supports it. No destination or credentials exist yet, so off-site backup is **not working until configured and tested** (step 5).

## 4. Restore
Stop the site first.
```bash
# Docker
docker compose stop web
docker compose run --rm --entrypoint python web /app/tools/restore.py /data/backups/redecor-backup-YYYYmmdd-HHMMSS.zip --db /data/redecor.db --uploads /data/uploads
docker compose start web
```
```powershell
# Windows, local
python tools\restore.py D:\Backups\redecor\redecor-backup-YYYYmmdd-HHMMSS.zip --db backend\redecor.db --uploads backend\uploads
```
`restore.py` verifies the zip before touching anything. It then **moves** the current database and uploads aside (`…before-restore-<time>`) instead of deleting them, so a wrong restore can be undone.

**PostgreSQL:** `psql "$DATABASE_URL" -f redecor.sql`, run on an empty database.

## 5. Restore test (do it once before launch, then every 3 months)
1. Take a fresh backup: `docker compose exec backup python /app/tools/backup.py --db /data/redecor.db --uploads /data/uploads --out-dir /data/backups`.
2. Copy the zip to a laptop and run `python tools/backup.py --verify <zip>`.
3. Restore it into an empty folder with `tools/restore.py` and start a local backend with `DATABASE_URL`/`UPLOAD_DIR` pointing there.
4. Open the site and admin locally: projects, photos and enquiries must all be present.
5. Write the date and result in the launch checklist.

The automated test `backend/tests/test_backup.py` performs the same round trip on every test run:
- backup
- retention
- off-site copy
- corruption detection
- restore with "move aside"
