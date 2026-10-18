# Moving the site to a server

The whole site is one container: the API, the admin and the built website. Data (database and photos) lives in one folder.

## Option A: Docker on any VPS (recommended)
1. Install Docker on the server, copy this repository to it (`git clone`).
2. `cp .env.example .env` and edit it: a long random `SECRET_KEY`, your `ADMIN_EMAIL` / `ADMIN_PASSWORD`, `SITE_URL=https://your-domain.com`, `SEED_DEMO=0`.
3. `docker compose up -d --build` — the site answers on port 8000.
4. Put HTTPS in front (Caddy is the easiest: `your-domain.com { reverse_proxy localhost:8000 }`), point the domain's DNS at the server.
5. Log in at `/admin`, add real projects.

## Option B: no Docker
`cd frontend && npm ci && npm run build`, then in `backend/`: `pip install -r requirements.txt` and
`uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'` (use systemd or a process manager so it restarts). Same `.env` values as above.

## Taking your current data with you
On the old machine: `python tools/backup.py` creates a zip with the database and all photos.
On the new server: put `redecor.db` and the `uploads/` folder into the Docker volume (`/data`) or next to the backend, then start the site.

## Updating later
`git pull && docker compose up -d --build`. New database columns are added automatically at startup; data is never deleted.

## Checklist before going public
- `SEED_DEMO=0`, a new `SECRET_KEY`, a strong admin password (change the one used while testing).
- Remove the two TEST projects: `python tools/seed_test_projects.py --api https://your-domain.com --email you --delete`.
- Daily `tools/backup.py` (cron) copied off the server.
