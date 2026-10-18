import os
from pathlib import Path


def _load_dotenv() -> None:
    env = Path(__file__).resolve().parent.parent / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    app_env: str = os.getenv("APP_ENV", "development").strip().lower()
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'redecor.db'}")
    secret_key: str = os.getenv("SECRET_KEY", "")
    admin_email: str = os.getenv("ADMIN_EMAIL", "").strip().lower()
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    site_url: str = os.getenv("SITE_URL", "http://localhost:8000").rstrip("/")
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))).resolve()
    frontend_dist: Path = Path(
        os.getenv("FRONTEND_DIST", str(BASE_DIR.parent / "frontend" / "dist"))
    ).resolve()
    cors_origins: list[str] = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
    # Placeholder "[Project name]" demo content: off unless explicitly requested (local design work only).
    seed_demo: bool = _flag("SEED_DEMO", "0")
    # Projects with slugs starting "test-project-" are hidden from the public site unless this is on.
    allow_test_content: bool = _flag("ALLOW_TEST_CONTENT", "0")
    token_hours: int = int(os.getenv("TOKEN_HOURS", "12"))
    max_upload_bytes: int = 15 * 1024 * 1024
    max_document_bytes: int = 25 * 1024 * 1024

    # Enquiry e-mail notifications (any SMTP provider: Microsoft 365, Google Workspace, Zoho, cPanel...)
    smtp_host: str = os.getenv("SMTP_HOST", "").strip()
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "").strip()
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_security: str = os.getenv("SMTP_SECURITY", "starttls").strip().lower()  # starttls | ssl | none
    mail_from: str = os.getenv("MAIL_FROM", "").strip()
    notify_to: list[str] = [a.strip() for a in os.getenv("NOTIFY_TO", "").split(",") if a.strip()]
    notify_max_attempts: int = int(os.getenv("NOTIFY_MAX_ATTEMPTS", "5"))
    notify_retry_seconds: int = int(os.getenv("NOTIFY_RETRY_SECONDS", "600"))  # 0 disables the retry loop

    # Optional webhook (Slack / Teams / Discord / generic JSON) for operational alerts.
    alert_webhook_url: str = os.getenv("ALERT_WEBHOOK_URL", "").strip()
    # Where tools/backup.py writes; used by the health check to report the age of the last backup.
    backup_dir: str = os.getenv("BACKUP_DIR", "").strip()

    # Company social profiles (same as frontend/src/config.ts), used in structured data.
    social_links: list[str] = [
        u.strip()
        for u in os.getenv(
            "SOCIAL_LINKS",
            "https://www.linkedin.com/company/redecorgroup/,https://www.facebook.com/profile.php?id=61563487254805,"
            "https://www.instagram.com/redecor.egy,https://www.tiktok.com/@redecor.egy",
        ).split(",")
        if u.strip()
    ]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.mail_from and self.notify_to)


settings = Settings()
