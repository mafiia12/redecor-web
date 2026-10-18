import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp())
os.environ.update(
    DATABASE_URL=f"sqlite:///{_tmp / 'test.db'}",
    UPLOAD_DIR=str(_tmp / "uploads"),
    FRONTEND_DIST=str(_tmp / "nodist"),
    ADMIN_EMAIL="admin@test.com",
    ADMIN_PASSWORD="correct-horse-battery",
    SECRET_KEY="test-secret-key-that-is-long-enough-123456",
    NOTIFY_RETRY_SECONDS="0",
    SEED_DEMO="1",
)

import io  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.main import app  # noqa: E402
from app.routers import admin, public  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_limiters():
    public.enquiry_limiter.reset()
    admin.login_limiter.reset()
    admin.account_limiter.reset()
    public.event_limiter.reset()


@pytest.fixture()
def auth(client):
    r = client.post("/api/admin/login", json={"email": "admin@test.com", "password": "correct-horse-battery"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def make_png(w=1200, h=800, color=(180, 120, 60)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, "PNG")
    return buf.getvalue()
