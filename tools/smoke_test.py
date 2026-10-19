#!/usr/bin/env python3
"""Read-only smoke test for a deployed Redecor site.

Usage:
    python tools/smoke_test.py --base-url https://new.redecorgroup.com [--insecure] [--json out.json]
                               [--host-header new.redecorgroup.com] [--timeout 15]

Only GET/HEAD requests are made; it never logs in and never submits forms. Redirects are not
followed automatically. Prints a PASS/FAIL table, writes JSON results (default smoke_result.json)
and exits 1 on any FAIL.
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from urllib.parse import urlparse, urlunparse

USER_AGENT = "redecor-smoke-test/1.0"


@dataclass
class Response:
    status: int
    headers: dict[str, str]  # lower-cased names
    body: str
    error: str = ""


@dataclass
class Result:
    name: str
    ok: bool
    detail: str


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


class Client:
    def __init__(self, base_url: str, insecure: bool = False, host_header: str | None = None, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.host_header = host_header
        self.timeout = timeout
        ctx = ssl.create_default_context()
        if insecure:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        self.opener = urllib.request.build_opener(_NoRedirect(), urllib.request.HTTPSHandler(context=ctx))

    def url(self, path: str) -> str:
        return self.base_url + path

    def request(self, url: str, method: str = "GET", max_bytes: int = 2_000_000) -> Response:
        if method not in ("GET", "HEAD"):
            raise ValueError("smoke test is read-only")
        if urlparse(url).scheme not in ("http", "https"):
            raise ValueError("only http(s) URLs")
        headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
        if self.host_header:
            headers["Host"] = self.host_header
        req = urllib.request.Request(url, method=method, headers=headers)  # noqa: S310 (scheme checked above)
        try:
            resp = self.opener.open(req, timeout=self.timeout)
        except urllib.error.HTTPError as exc:  # 3xx (not followed), 4xx, 5xx
            resp = exc
        except (urllib.error.URLError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            return Response(0, {}, "", error=str(reason))
        with resp:
            raw = resp.read(max_bytes) if method == "GET" else b""
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            status = resp.status if hasattr(resp, "status") else resp.code
        return Response(status, hdrs, raw.decode("utf-8", errors="replace"))

    def get(self, path: str) -> Response:
        return self.request(self.url(path))


def _desc(r: Response) -> str:
    return f"error: {r.error}" if r.error else f"HTTP {r.status}"


def _html_tag(body: str) -> str:
    m = re.search(r"<html\b[^>]*>", body, re.I)
    return m.group(0) if m else ""


def _attr(tag: str, name: str) -> str | None:
    m = re.search(rf'\b{name}\s*=\s*["\']([^"\']*)["\']', tag, re.I)
    return m.group(1) if m else None


def _meta_tags(body: str) -> list[str]:
    return re.findall(r"<meta\b[^>]*>", body, re.I)


def run_checks(c: Client) -> list[Result]:
    results: list[Result] = []

    def add(name: str, ok: bool, detail: str) -> None:
        results.append(Result(name, ok, detail))

    base = urlparse(c.base_url)
    is_https = base.scheme == "https"
    expected_host = (c.host_header or base.hostname or "").split(":")[0].lower()

    # language/direction of home pages
    home = c.get("/")
    for path, lang, direction, r in (("/", "en", "ltr", home), ("/ar", "ar", "rtl", c.get("/ar"))):
        tag = _html_tag(r.body)
        ok = r.status == 200 and (_attr(tag, "lang") or "").lower().startswith(lang) and (_attr(tag, "dir") or "").lower() == direction
        add(f"GET {path} lang={lang} dir={direction}", ok, f"{_desc(r)}; {tag[:80] or 'no <html> tag'}")

    # key routes
    for path in ("/projects", "/about", "/contact", "/services/fitout", "/privacy", "/ar/projects", "/ar/contact"):
        r = c.get(path)
        add(f"GET {path}", r.status == 200, _desc(r))

    # 404
    r = c.get("/this-page-does-not-exist-smoke")
    add("unknown page returns 404", r.status == 404, _desc(r))

    # readiness
    r = c.get("/api/health/ready")
    ok, detail = False, _desc(r)
    if r.status in (200, 503):
        try:
            data = json.loads(r.body)
            ok = isinstance(data, dict) and "ok" in data
            detail += f"; ok={data.get('ok')!r}" if isinstance(data, dict) else "; not a JSON object"
        except ValueError:
            detail += "; body is not JSON"
    add("GET /api/health/ready", ok, detail)

    # http -> https redirect
    if is_https:
        http_url = urlunparse(base._replace(scheme="http", netloc=base.hostname or "")) + "/"
        r = c.request(http_url)
        loc = r.headers.get("location", "")
        ok = r.status in (301, 308) and loc.startswith("https://")
        add("http:// redirects to https://", ok, f"{_desc(r)}; Location={loc or '-'}")

    # security headers
    h = home.headers
    csp = h.get("content-security-policy", "")
    add("header Content-Security-Policy", bool(csp), "present" if csp else "missing")
    xcto = h.get("x-content-type-options", "")
    add("header X-Content-Type-Options=nosniff", xcto.lower() == "nosniff", xcto or "missing")
    rp = h.get("referrer-policy", "")
    add("header Referrer-Policy", bool(rp), rp or "missing")
    xfo = h.get("x-frame-options", "")
    fa = "frame-ancestors" in csp.lower()
    add("frame protection", bool(xfo) or fa, f"X-Frame-Options={xfo or '-'}; CSP frame-ancestors={'yes' if fa else 'no'}")
    if is_https:
        hsts = h.get("strict-transport-security", "")
        add("header Strict-Transport-Security", "max-age" in hsts.lower(), hsts or "missing")

    # robots + sitemap
    r = c.get("/robots.txt")
    add("GET /robots.txt", r.status == 200, _desc(r))
    r = c.get("/sitemap.xml")
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.body, re.I)
    bad = [u for u in locs if (urlparse(u).hostname or "").lower() != expected_host]
    ok = r.status == 200 and bool(locs) and not bad
    detail = f"{_desc(r)}; {len(locs)} <loc>"
    if bad:
        detail += f"; {len(bad)} with wrong host, e.g. {bad[0]}"
    elif r.status == 200 and not locs:
        detail += "; no <loc> entries"
    add(f"GET /sitemap.xml (hosts = {expected_host})", ok, detail)

    # open graph
    metas = _meta_tags(home.body)
    for prop in ("og:title", "og:description", "og:image"):
        found = [m for m in metas if (_attr(m, "property") or _attr(m, "name") or "").lower() == prop and _attr(m, "content")]
        add(f"home meta {prop}", bool(found), "present" if found else "missing")

    # admin not indexable
    r = c.get("/admin")
    xrt = r.headers.get("x-robots-tag", "").lower()
    meta_noindex = any(
        (_attr(m, "name") or "").lower() == "robots" and "noindex" in (_attr(m, "content") or "").lower() for m in _meta_tags(r.body)
    )
    add("/admin is noindex", "noindex" in xrt or meta_noindex, f"{_desc(r)}; X-Robots-Tag={xrt or '-'}; meta robots noindex={meta_noindex}")

    # private attachments not public
    for path in ("/media/attachments/x.pdf", "/attachments/x.pdf", "/uploads/attachments/x.pdf"):
        r = c.get(path)
        add(f"GET {path} not served", r.status in (403, 404), f"{_desc(r)}; content-type={r.headers.get('content-type', '-')}")

    return results


def print_table(results: list[Result]) -> None:
    width = max(len(r.name) for r in results)
    for r in results:
        print(f"{'PASS' if r.ok else 'FAIL'}  {r.name.ljust(width)}  {r.detail}")
    failed = sum(not r.ok for r in results)
    print()
    print(f"{len(results) - failed} passed, {failed} failed")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Read-only smoke test of a deployed Redecor site.")
    ap.add_argument("--base-url", required=True, help="e.g. https://new.redecorgroup.com")
    ap.add_argument("--insecure", action="store_true", help="do not verify TLS certificates (local Caddy internal CA)")
    ap.add_argument("--host-header", help="send this Host header (testing Caddy by IP)")
    ap.add_argument("--json", default="smoke_result.json", help="where to write JSON results")
    ap.add_argument("--timeout", type=float, default=15.0)
    args = ap.parse_args(argv)

    if urlparse(args.base_url).scheme not in ("http", "https"):
        ap.error("--base-url must start with http:// or https://")

    client = Client(args.base_url, insecure=args.insecure, host_header=args.host_header, timeout=args.timeout)
    results = run_checks(client)
    print_table(results)
    failed = sum(not r.ok for r in results)
    payload = {"base_url": args.base_url, "passed": len(results) - failed, "failed": failed, "results": [asdict(r) for r in results]}
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print(f"results written to {args.json}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
