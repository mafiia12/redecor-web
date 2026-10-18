#!/usr/bin/env python3
"""Validate a Redecor .env file before deploying.

Usage:
    python tools/check_env.py path/to/.env [--production-required]

Prints a table of every known variable with status ``set``/``empty`` (values are NEVER printed),
then FAIL/WARN lines and a summary. Exits 1 if any FAIL.

``--production-required`` applies the production rules even if APP_ENV is not ``production``
(useful to check a staging file is production-grade).

Tests import :func:`check` directly: ``check(env, mode_bits) -> (fails, warns)``.
"""

from __future__ import annotations

import argparse
import os
import re
import stat
import sys
from pathlib import Path
from urllib.parse import urlparse

# name -> spec. "prod" = required when APP_ENV=production; "required" = always required.
# type: str | int | float | bool | url | email-list | enum | hhmm | tz
SCHEMA: dict[str, dict] = {
    "APP_ENV": {"type": "enum", "values": ["development", "staging", "production"], "required": True, "prod": True, "default": None, "description": "Environment name"},
    "SITE_DOMAIN": {"type": "str", "prod": True, "default": None, "description": "Domain Caddy serves (no scheme)"},
    "SITE_URL": {"type": "url", "prod": True, "default": None, "description": "Public base URL (https:// in production)"},
    "PRIMARY_DOMAIN": {"type": "str", "prod": False, "default": "redecorgroup.com", "description": "Canonical/primary domain"},
    "SECRET_KEY": {"type": "str", "required": True, "prod": True, "default": None, "description": "Token signing key, 32+ random chars"},
    "ADMIN_EMAIL": {"type": "str", "prod": True, "default": None, "description": "First admin account e-mail"},
    "ADMIN_PASSWORD": {"type": "str", "prod": False, "default": None, "description": "First admin password (only used when no admin exists)"},
    "SEED_DEMO": {"type": "bool", "prod": False, "default": "0", "description": "Seed demo content"},
    "ALLOW_TEST_CONTENT": {"type": "bool", "prod": False, "default": "0", "description": "Allow test content"},
    "ENFORCE_APPROVALS": {"type": "bool", "prod": False, "default": "1", "description": "Require approval before publishing"},
    "DATABASE_URL": {"type": "str", "prod": False, "default": None, "description": "SQLAlchemy database URL"},
    "UPLOAD_DIR": {"type": "str", "prod": False, "default": None, "description": "Public uploads directory"},
    "ATTACHMENTS_DIR": {"type": "str", "prod": False, "default": None, "description": "Private enquiry attachments directory"},
    "BACKUP_DIR": {"type": "str", "prod": False, "default": None, "description": "Backup output directory"},
    "FRONTEND_DIST": {"type": "str", "prod": False, "default": None, "description": "Built frontend directory"},
    "CORS_ORIGINS": {"type": "str", "prod": False, "default": None, "description": "Comma-separated allowed origins"},
    "TOKEN_HOURS": {"type": "int", "prod": False, "default": None, "description": "Admin session length in hours"},
    "HEALTH_TOKEN": {"type": "str", "prod": False, "default": None, "description": "Token for detailed health endpoint"},
    "REDIRECTS_FILE": {"type": "str", "prod": False, "default": None, "description": "Old-site redirect map file"},
    "SMTP_HOST": {"type": "str", "prod": False, "default": None, "description": "SMTP server"},
    "SMTP_PORT": {"type": "int", "prod": False, "default": "587", "description": "SMTP port"},
    "SMTP_SECURITY": {"type": "enum", "values": ["starttls", "ssl", "none"], "prod": False, "default": "starttls", "description": "SMTP transport security"},
    "SMTP_USER": {"type": "str", "prod": False, "default": None, "description": "SMTP username"},
    "SMTP_PASSWORD": {"type": "str", "prod": False, "default": None, "description": "SMTP password"},
    "MAIL_FROM": {"type": "str", "prod": False, "default": None, "description": "Sender address"},
    "NOTIFY_TO": {"type": "email-list", "prod": False, "default": None, "description": "Comma-separated enquiry recipients"},
    "NOTIFY_MAX_ATTEMPTS": {"type": "int", "prod": False, "default": None, "description": "Notification retry attempts"},
    "NOTIFY_RETRY_SECONDS": {"type": "int", "prod": False, "default": None, "description": "Seconds between retries"},
    "DIGEST_TIME": {"type": "hhmm", "prod": False, "default": None, "description": "Daily digest time HH:MM (empty = disabled)"},
    "DIGEST_TZ": {"type": "tz", "prod": False, "default": "Africa/Cairo", "description": "Digest time zone"},
    "VIRUS_SCAN_ENABLED": {"type": "bool", "prod": False, "default": "0", "description": "Scan attachments with ClamAV"},
    "CLAMAV_HOST": {"type": "str", "prod": False, "default": None, "description": "ClamAV host"},
    "CLAMAV_PORT": {"type": "int", "prod": False, "default": None, "description": "ClamAV port"},
    "ATTACH_MAX_FILE_MB": {"type": "int", "prod": False, "default": None, "description": "Max size per attachment (MB)"},
    "ATTACH_MAX_FILES": {"type": "int", "prod": False, "default": None, "description": "Max attachments per enquiry"},
    "ATTACH_MAX_TOTAL_MB": {"type": "int", "prod": False, "default": None, "description": "Max total attachment size (MB)"},
    "IMAGE_MIN_LONG_EDGE": {"type": "int", "prod": False, "default": None, "description": "Min image long edge (px)"},
    "IMAGE_MIN_COVER_LONG_EDGE": {"type": "int", "prod": False, "default": None, "description": "Min cover image long edge (px)"},
    "IMAGE_ASPECT_MIN": {"type": "float", "prod": False, "default": None, "description": "Min image aspect ratio"},
    "IMAGE_ASPECT_MAX": {"type": "float", "prod": False, "default": None, "description": "Max image aspect ratio"},
    "ALERT_WEBHOOK_URL": {"type": "url", "https_only": True, "prod": False, "default": None, "description": "Alert webhook (https://)"},
    "BACKUP_KEEP": {"type": "int", "prod": False, "default": None, "description": "Number of backups to keep"},
    "BACKUP_COPY_TO": {"type": "str", "prod": False, "default": None, "description": "Second (off-server) backup location"},
    "SOCIAL_LINKS": {"type": "str", "prod": False, "default": None, "description": "Social media links"},
}

DEV_SECRET_MARKERS = ("change-me", "changeme", "test-secret", "e2e-secret", "secret")
MIN_SECRET_LEN = 32
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}
EMAIL_RE = re.compile(r"^[^@\s,]+@[^@\s,]+\.[^@\s,]+$")
HHMM_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def parse_env_text(text: str) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif " #" in value:  # inline comment on an unquoted value
            value = value.split(" #", 1)[0].rstrip()
        env[key] = value
    return env


def _example_placeholder() -> str:
    example = Path(__file__).resolve().parents[1] / ".env.example"
    try:
        return parse_env_text(example.read_text(encoding="utf-8")).get("SECRET_KEY", "")
    except OSError:
        return ""


def _as_bool(value: str) -> bool | None:
    v = value.strip().lower()
    if v in TRUE_VALUES:
        return True
    if v in FALSE_VALUES:
        return False
    return None


def _type_error(name: str, spec: dict, value: str) -> str | None:
    t = spec["type"]
    if t == "int":
        try:
            int(value)
        except ValueError:
            return f"{name} must be an integer"
    elif t == "float":
        try:
            float(value)
        except ValueError:
            return f"{name} must be a number"
    elif t == "bool":
        if _as_bool(value) is None:
            return f"{name} must be 0/1 (or true/false)"
    elif t == "enum":
        if value not in spec["values"]:
            return f"{name} must be one of: {', '.join(spec['values'])}"
    elif t == "url":
        p = urlparse(value)
        if p.scheme not in ("http", "https") or not p.hostname:
            return f"{name} must be a full http(s):// URL"
        if spec.get("https_only") and p.scheme != "https":
            return f"{name} must start with https://"
    elif t == "email-list":
        items = [x.strip() for x in value.split(",") if x.strip()]
        if not items or any(not EMAIL_RE.match(x) for x in items):
            return f"{name} must be a comma-separated list of e-mail addresses"
    elif t == "hhmm":
        if not HHMM_RE.match(value):
            return f"{name} must be HH:MM (24h) or empty"
    elif t == "tz":
        try:
            from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        except ImportError:  # pragma: no cover
            return None
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            return f"{name} is not a known time zone"
        except Exception:  # noqa: BLE001  (no tzdata installed: cannot validate)
            return None
    return None


def check(env: dict[str, str], mode_bits: int | None = None, production_required: bool = False) -> tuple[list[str], list[str]]:
    """Return (fails, warns). Messages never contain variable values."""
    fails: list[str] = []
    warns: list[str] = []

    def val(name: str) -> str:
        return (env.get(name) or "").strip()

    app_env = val("APP_ENV")
    prod = app_env == "production" or production_required

    # unknown keys
    for key in sorted(env):
        if key not in SCHEMA:
            warns.append(f"{key} is not a known variable (typo?)")

    # required
    for name, spec in SCHEMA.items():
        if not val(name) and (spec.get("required") or (prod and spec.get("prod"))):
            why = "always" if spec.get("required") else "in production"
            fails.append(f"{name} is required ({why})")

    # types
    for name, spec in SCHEMA.items():
        v = val(name)
        if v:
            err = _type_error(name, spec, v)
            if err:
                fails.append(err)

    # secret strength
    secret = val("SECRET_KEY")
    if secret:
        placeholder = _example_placeholder()
        lowered = secret.lower()
        if len(secret) < MIN_SECRET_LEN:
            fails.append(f"SECRET_KEY is shorter than {MIN_SECRET_LEN} characters")
        if any(m in lowered for m in DEV_SECRET_MARKERS) or (placeholder and secret == placeholder):
            fails.append("SECRET_KEY looks like a dev/default value; generate a random one")

    # production safety switches
    if prod:
        if _as_bool(val("SEED_DEMO") or "0") is True:
            fails.append("SEED_DEMO=1 is not allowed in production")
        if _as_bool(val("ALLOW_TEST_CONTENT") or "0") is True:
            fails.append("ALLOW_TEST_CONTENT=1 is not allowed in production")
        if _as_bool(val("ENFORCE_APPROVALS") or "1") is False:
            fails.append("ENFORCE_APPROVALS=0 is not allowed in production")
        if val("SITE_URL") and urlparse(val("SITE_URL")).scheme != "https":
            fails.append("SITE_URL must use https:// in production")

    site_url, site_domain = val("SITE_URL"), val("SITE_DOMAIN")
    if site_url and site_domain:
        host = (urlparse(site_url).hostname or "").lower()
        if host and host != site_domain.lower().rstrip("."):
            fails.append("SITE_URL host does not match SITE_DOMAIN")

    # SMTP consistency
    smtp_core = ["SMTP_HOST", "MAIL_FROM", "NOTIFY_TO"]
    core_set = [n for n in smtp_core if val(n)]
    smtp_on = len(core_set) == len(smtp_core)
    if core_set and not smtp_on:
        missing = [n for n in smtp_core if not val(n)]
        fails.append(f"SMTP partially configured: also set {', '.join(missing)} (or clear them all)")
    if bool(val("SMTP_USER")) != bool(val("SMTP_PASSWORD")):
        fails.append("SMTP_USER and SMTP_PASSWORD must both be set or both empty")
    if not val("SMTP_HOST"):
        # SMTP_PORT / SMTP_SECURITY have harmless defaults (as in .env.example); credentials do not.
        stray = [n for n in ("SMTP_USER", "SMTP_PASSWORD") if val(n)]
        if stray and not core_set:
            fails.append(f"SMTP partially configured: {', '.join(stray)} set but SMTP_HOST empty")

    # file permissions
    if mode_bits is not None and os.name == "posix" and mode_bits & (stat.S_IRWXG | stat.S_IRWXO):
        fails.append(f"file permissions {oct(mode_bits & 0o777)} are too open; run: chmod 600 <file>")

    # disabled optional features
    if not smtp_on:
        warns.append("SMTP not configured: no enquiry e-mails will be sent")
    if not val("DIGEST_TIME"):
        warns.append("DIGEST_TIME empty: daily digest disabled")
    elif not smtp_on:
        warns.append("DIGEST_TIME set but SMTP is off: daily digest disabled")
    if _as_bool(val("VIRUS_SCAN_ENABLED") or "0") is not True:
        warns.append("VIRUS_SCAN_ENABLED=0: attachments are not virus-scanned")
    if not val("BACKUP_COPY_TO"):
        warns.append("BACKUP_COPY_TO empty: no off-server backup copy")
    if not val("ALERT_WEBHOOK_URL"):
        warns.append("ALERT_WEBHOOK_URL empty: no alerts on failures")
    if not val("ADMIN_PASSWORD"):
        warns.append("ADMIN_PASSWORD empty: fine if an admin already exists; required on first run")

    return fails, warns


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate a Redecor .env file (values are never printed).")
    ap.add_argument("env_file", type=Path)
    ap.add_argument("--production-required", action="store_true", help="apply production rules regardless of APP_ENV")
    args = ap.parse_args(argv)

    try:
        text = args.env_file.read_text(encoding="utf-8")
        mode_bits = stat.S_IMODE(args.env_file.stat().st_mode) if os.name == "posix" else None
    except OSError as exc:
        print(f"FAIL  cannot read {args.env_file}: {exc.strerror}")
        return 1

    env = parse_env_text(text)
    fails, warns = check(env, mode_bits, production_required=args.production_required)

    width = max(len(n) for n in SCHEMA)
    print(f"{'VARIABLE'.ljust(width)}  STATUS")
    for name in SCHEMA:
        status = "set" if (env.get(name) or "").strip() else "empty"
        print(f"{name.ljust(width)}  {status}")
    print()
    for f in fails:
        print(f"FAIL  {f}")
    for w in warns:
        print(f"WARN  {w}")
    print()
    print(f"{'FAILED' if fails else 'OK'}: {len(fails)} fail(s), {len(warns)} warning(s) in {args.env_file}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
