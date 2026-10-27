"""Per-address cap on POST /api/auth/register.

Login, password reset and password change were all throttled, but
registration accepted unlimited requests: a script could create accounts
in bulk (e.g. squatting addresses before their owners sign up -- see
routers/auth._link_by_email) or walk a list of emails through the
"email already registered" answer to learn who has an account.

Every attempt counts, accepted or refused, in a one-hour sliding window per
public address. The allowance is deliberately generous: a whole classroom
behind one school router signs up from the same address, and it must
never be locked out -- this only has to stop a script. Private, loopback
and unknown addresses are never limited (they mean our own proxy or a
shared NAT, as in login_throttle), so a wrong TRUSTED_PROXY_HOPS fails
open, never into locking everyone out. In-process like the other limits:
production runs one uvicorn worker, and a restart only forgives.
"""

from __future__ import annotations

import math
import threading
import time

from app.services.login_throttle import _is_global

WINDOW_SECONDS = 60 * 60
LIMIT_PER_HOUR = 40

LIMITED_DETAIL = "Too many sign-ups from this network. Please try again later."

_now = time.monotonic  # replaced in tests
_guard = threading.Lock()
_hits: dict[str, list[float]] = {}
_MAX_KEYS = 50_000  # a flood of addresses must not grow memory forever


def check(ip: str | None) -> int:
    """Record one registration attempt from `ip`. 0 when it may go ahead,
    else the seconds until the oldest counted attempt leaves the window."""
    if not _is_global(ip):
        return 0
    now = _now()
    with _guard:
        hits = [t for t in _hits.get(ip, []) if now - t < WINDOW_SECONDS]
        if len(hits) >= LIMIT_PER_HOUR:
            _hits[ip] = hits
            return max(1, math.ceil(hits[0] + WINDOW_SECONDS - now))
        hits.append(now)
        _hits[ip] = hits
        if len(_hits) > _MAX_KEYS:
            _hits.clear()
        return 0


def reset() -> None:
    """Tests: forget every counter."""
    with _guard:
        _hits.clear()
