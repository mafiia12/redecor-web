import hashlib
import hmac
import logging
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User

log = logging.getLogger("redecor")

if not settings.secret_key:
    settings.secret_key = secrets.token_urlsafe(48)
    log.warning("SECRET_KEY is not set: using a random key. Admin sessions reset on every restart.")

_N, _R, _P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_hex, hash_hex = stored.split("$")
        dk = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=_N, r=_R, p=_P, dklen=32)
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


ROLES = ("viewer", "editor", "admin")  # increasing rights

_COMMON = {"password", "123456789", "qwerty", "redecor", "admin", "letmein", "welcome"}


def password_problems(password: str, email: str = "") -> list[str]:
    """Simple, practical policy: long passphrases beat complexity rules."""
    problems = []
    if len(password) < 12:
        problems.append("Use at least 12 characters.")
    if len(password) > 200:
        problems.append("Use at most 200 characters.")
    if not any(c.isalpha() for c in password) or not any(not c.isalpha() for c in password):
        problems.append("Mix letters with numbers or symbols.")
    low = password.lower()
    local = email.split("@")[0].lower()
    if (local and len(local) >= 4 and local in low) or any(w in low for w in _COMMON):
        problems.append("Avoid your e-mail name and common words.")
    return problems


def create_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": user.email, "ver": user.token_version or 0, "iat": now, "exp": now + timedelta(hours=settings.token_hours)}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


_bearer = HTTPBearer(auto_error=False)


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)
) -> User:
    unauth = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    if not creds:
        raise unauth
    try:
        payload = jwt.decode(
            creds.credentials, settings.secret_key, algorithms=["HS256"], options={"require": ["exp", "iat", "sub"]}
        )
    except jwt.PyJWTError:
        raise unauth from None
    user = db.scalar(select(User).where(User.email == payload.get("sub")))
    if not user or payload.get("ver", 0) != (user.token_version or 0):
        raise unauth
    return user


def require_role(minimum: str):
    """Dependency: the signed-in user must have at least this role. Enforced on the server for every endpoint."""
    need = ROLES.index(minimum)

    def dep(user: User = Depends(current_user)) -> User:
        role = user.role if user.role in ROLES else "viewer"
        if ROLES.index(role) < need:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role does not allow this action")
        return user

    return dep


viewer = require_role("viewer")
editor = require_role("editor")
admin_only = require_role("admin")


class RateLimiter:
    """Small in-memory sliding-window limiter (per process). Use a shared store if you scale out."""

    def __init__(self, limit: int, window_s: int):
        self.limit, self.window = limit, window_s
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests. Please try again later.")
        q.append(now)
        if len(self.hits) > 5000:  # keep memory bounded
            for k in [k for k, v in self.hits.items() if not v]:
                del self.hits[k]

    def reset(self) -> None:
        self.hits.clear()


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
