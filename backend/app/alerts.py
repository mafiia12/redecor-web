"""Optional operational alerts to a webhook (Slack / Teams / Discord / any JSON endpoint).
Never raises: monitoring must not break the request that triggered it."""

import json
import logging
import threading
import time
import urllib.request

from .config import settings

log = logging.getLogger("redecor.alerts")
_last: dict[str, float] = {}
_lock = threading.Lock()


def alert(kind: str, message: str, min_interval_s: int = 900) -> bool:
    """Send at most one alert per kind every `min_interval_s`. Returns True when an alert was sent."""
    log.warning("ALERT %s: %s", kind, message)
    if not settings.alert_webhook_url.startswith("https://"):
        return False  # only https webhooks (never file: or other schemes)
    with _lock:
        now = time.monotonic()
        if now - _last.get(kind, -1e9) < min_interval_s:
            return False
        _last[kind] = now
    text = f"[Redecor website] {kind}: {message}"
    body = json.dumps({"text": text, "content": text}).encode()
    req = urllib.request.Request(settings.alert_webhook_url, data=body, headers={"Content-Type": "application/json"})  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=8):  # noqa: S310 (URL comes from the operator's env)
            return True
    except Exception as e:  # noqa: BLE001
        log.error("Alert webhook failed: %s", type(e).__name__)
        return False
