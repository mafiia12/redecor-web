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


class Settings:
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
    seed_demo: bool = os.getenv("SEED_DEMO", "1") == "1"
    token_hours: int = 12
    max_upload_bytes: int = 15 * 1024 * 1024


settings = Settings()
