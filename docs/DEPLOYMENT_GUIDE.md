# Deployment guide (Windows / PowerShell friendly)

Nothing in this repository deploys anything by itself. Publishing the site, changing DNS and creating accounts
(server, e-mail, monitoring) are owner decisions and actions.

## 0. What you deploy
One Docker image contains:
- the FastAPI backend
- the built React site
- the backup and restore tools

`docker-compose.yml` runs three services:

| Service | Role |
|---|---|
| `caddy` | HTTPS on ports 80/443 with automatic Let's Encrypt certificates (`deploy/Caddyfile`) |
| `web` | the site and API, reachable only from Caddy and from `127.0.0.1:8000` on the server |
| `backup` | a verified backup every 24 h into the data volume |

All data lives in the Docker volume `redecor-data` (`/data` in the containers):
- `redecor.db`
- `uploads/` (images and PDFs)
- `backups/`

## 1. Local development on Windows (VS Code terminal, PowerShell)
```powershell
cd "D:\Master Web (Redecor)\redecor-web"
git pull

# backend (terminal 1)
cd backend
python -m venv .venv            # first time only
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # first time only, then edit it (SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD)
uvicorn app.main:app --port 8001

# frontend (terminal 2)
cd frontend
npm install
npm run build                   # the backend serves the new build immediately (no restart needed any more)
```
- Site: http://localhost:8001. Admin: http://localhost:8001/admin.
- On first start after an update, the backend adds any new database columns automatically. Before doing so it saves a copy of the database next to it (`redecor.db.pre-migrate-<date>.bak`).

## 2. Production server (recommended: a small Linux VPS with Docker)
Minimum: 1 vCPU, 1–2 GB RAM, 25 GB disk, Ubuntu 22.04/24.04. Hostinger, DigitalOcean, Hetzner, AWS Lightsail or any similar provider works.

From Windows, open PowerShell and connect: `ssh root@SERVER_IP`. On the server:
```bash
curl -fsSL https://get.docker.com | sh          # installs Docker + compose plugin
git clone https://github.com/mafiia12/redecor-web.git && cd redecor-web
cp .env.example .env && nano .env               # fill it in (section 3)
docker compose up -d --build
docker compose ps                               # web should be "healthy"
curl -s http://127.0.0.1:8000/api/health/ready  # {"ok":true,...}
```
DNS: at the domain registrar, create an `A` record for `redecorgroup.com` (and `www`) pointing to SERVER_IP. Caddy gets the certificate on its own once DNS resolves. **Change DNS only when the owner approves the launch.**

Firewall: allow only 22 (SSH), 80 and 443. Port 8000 is bound to 127.0.0.1 and is not reachable from outside.

## 3. Production `.env`
| Variable | Value |
|---|---|
| `APP_ENV` | `production`. The app **refuses to start** with unsafe settings. |
| `SITE_DOMAIN` / `SITE_URL` | `redecorgroup.com` / `https://redecorgroup.com` |
| `SECRET_KEY` | 48+ random characters: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | First admin. Password: 12+ characters, letters plus numbers or symbols. Used only to create the account; change it later in /admin → My account. |
| `SEED_DEMO` / `ALLOW_TEST_CONTENT` | `0` / `0` (enforced in production) |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM`, `NOTIFY_TO` | Enquiry e-mails (section 4) |
| `ALERT_WEBHOOK_URL` | Optional `https://` Slack/Teams/Discord webhook for alerts |
| `BACKUP_KEEP`, `BACKUP_COPY_TO` | Backup retention and an optional second location (see BACKUP_AND_RECOVERY.md) |

Never commit `.env`. Never paste secrets into chats, tickets or documents.

## 4. Enquiry e-mail (SMTP)
Ask whoever manages the company mailbox for SMTP details. Common values:

| Provider | Host | Port | Security |
|---|---|---|---|
| Microsoft 365 | smtp.office365.com | 587 | starttls (account needs SMTP AUTH enabled) |
| Google Workspace | smtp.gmail.com | 587 | starttls (use an app password) |
| Zoho | smtp.zoho.com | 465 | ssl |
| cPanel hosting | mail.yourdomain | 465 / 587 | ssl / starttls |

Then in /admin → **Status & analytics** → **Send test e-mail**. Only a message accepted by the mail server is reported as sent. Every enquiry shows its e-mail status in /admin → Enquiries:
- E-mailed
- Failed (the error is shown, and there is a **Retry e-mail** button)
- Not configured

Failed e-mails are retried automatically every 10 minutes, up to 5 attempts.

## 5. Monitoring (external accounts needed)
- **Uptime:** create a free monitor (UptimeRobot, Better Stack…) for `https://redecorgroup.com/api/health/ready` (GET or HEAD). It returns 503 if the database or storage fails. It also reports failed notifications and the age of the last backup.
- **Alerts:** set `ALERT_WEBHOOK_URL`. The server posts there on:
  - unexpected server errors
  - notifications that failed after all retries
  - failed backups
- **Logs:** `docker compose logs -f web`. Logs rotate automatically (5 × 10 MB per service).

## 6. Updating the site
```bash
cd redecor-web
docker compose exec backup python /app/tools/backup.py --db /data/redecor.db --uploads /data/uploads --out-dir /data/backups   # backup first
git pull
docker compose up -d --build
docker compose ps
```

## 7. Rolling back a release
1. `git log --oneline` and choose the previous good commit.
2. `git checkout <commit> && docker compose up -d --build`.
3. New columns added by a newer version are harmless to older code (they are only ever added).
4. If data must go back too, restore the backup taken before the update (BACKUP_AND_RECOVERY.md §4).

## 8. Without Docker (Windows Server or a plain VM)
1. Install Python 3.12 and Node 20.
2. Run `npm ci && npm run build` in `frontend`.
3. Run `pip install -r requirements.txt` in `backend`.
4. Run uvicorn as a service:
   - NSSM on Windows
   - systemd on Linux

   Use this command: `uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips=127.0.0.1`
5. Put Caddy or IIS (ARR) in front for HTTPS.
6. Schedule `python tools/backup.py --out-dir D:\Backups\redecor --copy-to <second location>` daily (Task Scheduler / cron).
