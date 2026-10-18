# Stage 1: build the React site
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# Stage 2: FastAPI serves the API, the uploads and the built site
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production UPLOAD_DIR=/data/uploads DATABASE_URL=sqlite:////data/redecor.db \
    FRONTEND_DIST=/app/frontend/dist BACKUP_DIR=/data/backups ATTACHMENTS_DIR=/attachments REDIRECTS_FILE=/app/deploy/redirects.json
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/app backend/app
COPY tools/backup.py tools/restore.py tools/migrate.py tools/check_env.py tools/bulk_images.py tools/approval_gate_report.py tools/import_projects.py tools/
COPY deploy/redirects.json deploy/redirects.json
COPY --from=web /web/dist frontend/dist
# Run as an unprivileged user; /data is the only writable place (mount a volume there).
RUN useradd --system --uid 10001 --home /app redecor && mkdir -p /data /attachments && chown -R redecor /data /attachments
USER redecor
VOLUME /data /attachments
EXPOSE 8000
WORKDIR /app/backend
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health/ready', timeout=4).status == 200 else 1)"
# --proxy-headers: the real visitor IP comes from Caddy (rate limits). Port 8000 is never published to the internet.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*", "--no-server-header"]
