import importlib.util
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).parents[2] / "tools" / "check_env.py"
_spec = importlib.util.spec_from_file_location("check_env", _PATH)
check_env = importlib.util.module_from_spec(_spec)
sys.modules["check_env"] = check_env
_spec.loader.exec_module(check_env)

SECRET = "Zq8vN3kLp0Wx7RtY2bHm9JdF4aQe6UcG1sVn5KoP"


def prod_env(**overrides):
    env = {
        "APP_ENV": "production",
        "SITE_DOMAIN": "redecorgroup.com",
        "SITE_URL": "https://redecorgroup.com",
        "SECRET_KEY": SECRET,
        "ADMIN_EMAIL": "admin@redecorgroup.com",
        "ADMIN_PASSWORD": "Str0ng-Admin-Passphrase",
        "SEED_DEMO": "0",
        "ALLOW_TEST_CONTENT": "0",
        "ENFORCE_APPROVALS": "1",
        "SMTP_HOST": "smtp.office365.com",
        "SMTP_PORT": "587",
        "SMTP_SECURITY": "starttls",
        "SMTP_USER": "web@redecorgroup.com",
        "SMTP_PASSWORD": "smtp-pass-123",
        "MAIL_FROM": "web@redecorgroup.com",
        "NOTIFY_TO": "sales@redecorgroup.com, info@redecorgroup.com",
        "DIGEST_TIME": "08:30",
        "DIGEST_TZ": "Africa/Cairo",
        "VIRUS_SCAN_ENABLED": "1",
        "CLAMAV_HOST": "clamav",
        "CLAMAV_PORT": "3310",
        "ALERT_WEBHOOK_URL": "https://hooks.example.com/abc",
        "BACKUP_KEEP": "14",
        "BACKUP_COPY_TO": "/offsite",
    }
    env.update(overrides)
    return env


def fails_of(env, mode=0o600):
    return check_env.check(env, mode)[0]


def has(msgs, needle):
    return any(needle in m for m in msgs)


def test_valid_production_env_passes():
    fails, warns = check_env.check(prod_env(), 0o600)
    assert fails == []
    assert warns == []


@pytest.mark.parametrize("name", ["APP_ENV", "SECRET_KEY"])
def test_always_required(name):
    env = prod_env(APP_ENV="development")
    env[name] = ""
    assert has(fails_of(env), f"{name} is required")


@pytest.mark.parametrize("name", ["SITE_DOMAIN", "SITE_URL", "ADMIN_EMAIL"])
def test_required_in_production(name):
    env = prod_env()
    del env[name]
    assert has(fails_of(env), f"{name} is required")
    env["APP_ENV"] = "development"
    assert not has(fails_of(env), f"{name} is required")


def test_production_required_flag_applies_prod_rules():
    env = prod_env(APP_ENV="staging", SEED_DEMO="1")
    assert not has(fails_of(env), "SEED_DEMO")
    assert has(check_env.check(env, 0o600, production_required=True)[0], "SEED_DEMO")


def test_short_secret_fails():
    assert has(fails_of(prod_env(SECRET_KEY="Zq8vN3kLp0Wx7")), "shorter than 32")


@pytest.mark.parametrize(
    "value",
    [
        "change-me-change-me-change-me-change-me",
        "changeme-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "test-secret-key-that-is-long-enough-123456",
        "e2e-secret-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "my-super-SECRET-value-0123456789abcdef",
    ],
)
def test_dev_secret_fails(value):
    assert has(fails_of(prod_env(SECRET_KEY=value)), "dev/default")


def test_example_placeholder_secret_fails(monkeypatch):
    monkeypatch.setattr(check_env, "_example_placeholder", lambda: SECRET)
    assert has(fails_of(prod_env()), "dev/default")


@pytest.mark.parametrize(
    ("key", "value"),
    [("SEED_DEMO", "1"), ("ALLOW_TEST_CONTENT", "1"), ("ENFORCE_APPROVALS", "0")],
)
def test_production_safety_switches(key, value):
    assert has(fails_of(prod_env(**{key: value})), f"{key}={value}")
    assert not has(fails_of(prod_env(APP_ENV="staging", **{key: value})), f"{key}={value}")


def test_site_url_must_be_https_in_production():
    assert has(fails_of(prod_env(SITE_URL="http://redecorgroup.com")), "https://")


def test_site_url_host_must_match_domain():
    assert has(fails_of(prod_env(SITE_URL="https://other.com")), "does not match SITE_DOMAIN")


@pytest.mark.parametrize("missing", ["SMTP_HOST", "MAIL_FROM", "NOTIFY_TO"])
def test_smtp_core_group_partial(missing):
    assert has(fails_of(prod_env(**{missing: ""})), "SMTP partially configured")


@pytest.mark.parametrize("missing", ["SMTP_USER", "SMTP_PASSWORD"])
def test_smtp_credentials_pair(missing):
    assert has(fails_of(prod_env(**{missing: ""})), "SMTP_USER and SMTP_PASSWORD")


def test_smtp_credentials_without_host_is_partial():
    env = prod_env(SMTP_HOST="", MAIL_FROM="", NOTIFY_TO="")
    assert has(fails_of(env), "SMTP_HOST empty")


def test_smtp_fully_empty_is_ok():
    env = prod_env(SMTP_HOST="", MAIL_FROM="", NOTIFY_TO="", SMTP_USER="", SMTP_PASSWORD="")
    fails, warns = check_env.check(env, 0o600)
    assert fails == []
    assert has(warns, "SMTP not configured")


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("APP_ENV", "prod"),
        ("SMTP_SECURITY", "tls"),
        ("SMTP_PORT", "abc"),
        ("TOKEN_HOURS", "1.5"),
        ("SEED_DEMO", "maybe"),
        ("IMAGE_ASPECT_MIN", "wide"),
        ("NOTIFY_TO", "sales@redecorgroup.com, not-an-email"),
        ("DIGEST_TIME", "25:00"),
        ("DIGEST_TZ", "Mars/Olympus"),
        ("ALERT_WEBHOOK_URL", "http://hooks.example.com/abc"),
        ("SITE_URL", "redecorgroup.com"),
    ],
)
def test_bad_type_or_enum(key, value):
    assert has(fails_of(prod_env(**{key: value})), key)


@pytest.mark.parametrize("mode", [0o640, 0o604, 0o644, 0o660])
def test_loose_file_mode_fails(mode):
    assert has(fails_of(prod_env(), mode), "permissions")


def test_strict_file_mode_or_unknown_ok():
    assert not has(fails_of(prod_env(), 0o600), "permissions")
    assert not has(fails_of(prod_env(), None), "permissions")


def test_warnings_for_disabled_features():
    env = prod_env(
        SMTP_HOST="", MAIL_FROM="", NOTIFY_TO="", SMTP_USER="", SMTP_PASSWORD="",
        DIGEST_TIME="", VIRUS_SCAN_ENABLED="0", BACKUP_COPY_TO="", ALERT_WEBHOOK_URL="", ADMIN_PASSWORD="",
    )
    fails, warns = check_env.check(env, 0o600)
    assert fails == []
    for needle in ["SMTP not configured", "DIGEST_TIME", "VIRUS_SCAN_ENABLED", "BACKUP_COPY_TO", "ALERT_WEBHOOK_URL", "ADMIN_PASSWORD"]:
        assert has(warns, needle), needle


def test_digest_warns_when_smtp_off():
    env = prod_env(SMTP_HOST="", MAIL_FROM="", NOTIFY_TO="", SMTP_USER="", SMTP_PASSWORD="")
    assert has(check_env.check(env, 0o600)[1], "SMTP is off")


def test_unknown_key_warns():
    assert has(check_env.check(prod_env(SMTP_HOTS="x"), 0o600)[1], "SMTP_HOTS")


def test_parse_strips_quotes_and_comments():
    env = check_env.parse_env_text('# c\n\nA="quoted"\nB=\'single\'\nexport C=plain # note\nD=\n')
    assert env == {"A": "quoted", "B": "single", "C": "plain", "D": ""}


def test_main_never_prints_values(tmp_path, capsys):
    path = tmp_path / ".env"
    env = prod_env()
    path.write_text("".join(f"{k}={v}\n" for k, v in env.items()), encoding="utf-8")
    path.chmod(0o600)
    rc = check_env.main([str(path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "SECRET_KEY" in out
    for secret in (SECRET, "smtp-pass-123", "Str0ng-Admin-Passphrase", "hooks.example.com"):
        assert secret not in out


def test_main_exits_1_on_fail_without_leaking(tmp_path, capsys):
    path = tmp_path / ".env"
    bad = "short-but-secret-ish"
    path.write_text(f"APP_ENV=production\nSECRET_KEY={bad}\n", encoding="utf-8")
    path.chmod(0o644)
    rc = check_env.main([str(path)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "FAIL" in out
    assert bad not in out
