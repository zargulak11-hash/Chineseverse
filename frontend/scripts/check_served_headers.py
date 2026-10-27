# -*- coding: utf-8 -*-
"""Check the security headers a running ChineseVerse frontend really sends.

Read-only GET requests only. CI runs it against the image built from
frontend/Dockerfile (.github/workflows/frontend-image.yml); after a deploy it
can be pointed at the live site the same way:

    python frontend/scripts/check_served_headers.py http://127.0.0.1:8080
    python frontend/scripts/check_served_headers.py https://chineseverse.qobus.tj

src/securityHeaders.test.js checks the configuration files; this checks what
nginx actually answers, including the 404 page and redirects, and that the
report-only CSP's hashes match the inline script and handler in the page as
served (a hash taken from a Windows CRLF checkout once did not). Exits 1 on
any problem. Standard library only.
"""
import base64
import hashlib
import re
import sys
import time
import urllib.error
import urllib.request

REQUIRED = [
    "Strict-Transport-Security",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Permissions-Policy",
    "Content-Security-Policy-Report-Only",
]
SHORT = {
    "Strict-Transport-Security": "HSTS",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "XFO",
    "Referrer-Policy": "Referrer",
    "Permissions-Policy": "Perms",
    "Content-Security-Policy-Report-Only": "CSP-RO",
    "Cache-Control": "Cache",
}
# path -> expected status: public pages, the app shell, the 404 page (also
# the app shell) and a duplicate-address redirect.
PATHS = {"/": 200, "/download": 200, "/settings": 200, "/no-such-page-header-check": 404, "/index.html": 301}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # the 301 itself is what is checked
        return None


_open = urllib.request.build_opener(_NoRedirect).open


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "chineseverse-header-check"})
    try:
        with _open(req, timeout=20) as resp:
            return resp.status, resp.headers, resp.read()
    except urllib.error.HTTPError as err:  # 3xx/4xx/5xx still carry headers
        return err.code, err.headers, err.read()


def wait_until_up(base, seconds=30):
    deadline = time.time() + seconds
    while True:
        try:
            get(base + "/")
            return
        except OSError:
            if time.time() > deadline:
                raise
            time.sleep(1)


def sha256_source(text):
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode() + "'"


def main(base):
    base = base.rstrip("/")
    wait_until_up(base)
    problems = []

    def check(path, expected_status, extra=()):
        try:
            status, headers, body = get(base + path)
        except OSError as exc:  # unreachable / reset: a finding, not a crash
            problems.append(f"{path}: request failed ({type(exc).__name__}: {exc})")
            print(f"{path:<28} request failed")
            return None, b""
        line = [f"{path:<28} {status}"]
        if status != expected_status:
            problems.append(f"{path}: status {status}, expected {expected_status}")
        for name in [*REQUIRED, *extra]:
            n = len(headers.get_all(name) or [])
            line.append(f"{SHORT[name]}={n}")
            if n != 1:
                problems.append(f"{path}: {name} sent {n} times, expected once")
        if headers.get_all("Content-Security-Policy"):
            problems.append(f"{path}: an ENFORCED Content-Security-Policy is sent; it must stay report-only")
        server = headers.get("Server") or ""
        if re.search(r"\d", server):
            problems.append(f"{path}: Server header shows a version ({server!r})")
        print("  ".join(line))
        return headers, body

    headers, home = None, b""
    for path, expected in PATHS.items():
        h, body = check(path, expected)
        if path == "/":
            headers, home = h, body

    html = home.decode("utf-8", "replace")
    asset = re.search(r'src="(/assets/[^"]+\.js)"', html)
    if asset:
        check(asset.group(1), 200, extra=("Cache-Control",))
    else:
        problems.append("/: no /assets/*.js script found to check")

    csp = (headers.get("Content-Security-Policy-Report-Only") or "") if headers else ""
    script_src = next((d.split()[1:] for d in csp.split(";") if d.split()[:1] == ["script-src"]), [])
    inline = [
        m.group(2)
        for m in re.finditer(r"<script(?![^>]*\bsrc=)([^>]*)>([\s\S]*?)</script>", html)
        if 'type="application/ld+json"' not in m.group(1)
    ]
    handlers = re.findall(r'\son[a-z]+\s*=\s*"([^"]*)"', html)
    for kind, values in (("inline script", inline), ("inline handler", handlers)):
        for value in values:
            source = sha256_source(value)
            ok = source in script_src
            print(f"  served {kind} {source[:24]}...  allowed by CSP: {ok}")
            if not ok:
                problems.append(f"/: served {kind} hash {source} is not in the CSP script-src")
    if handlers and "'unsafe-hashes'" not in script_src:
        problems.append("/: inline handlers are hashed but 'unsafe-hashes' is missing")

    if problems:
        print("\nPROBLEMS:\n  " + "\n  ".join(problems))
        return 1
    print("\nall served headers ok")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: check_served_headers.py BASE_URL")
    sys.exit(main(sys.argv[1]))
