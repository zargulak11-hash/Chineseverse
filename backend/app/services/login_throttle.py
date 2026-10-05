"""Server-side brute-force protection for password sign-in.

POST /api/auth/login used to accept unlimited guesses, so a script could
try a password list against any username as fast as the API answered.
Failed attempts are now counted in three independent sliding windows, and
once one of them is over its allowance the login is refused with a 429 --
before the password is even checked -- until a short lock runs out:

- one account from one address ("pair"): a learner who mistypes a few
  times is only slowed down for that address, never locked out elsewhere;
- one account from any address ("account"): rotating addresses (a botnet,
  a proxy list) does not buy more guesses against the same account;
- one address against any account ("ip"): rotating usernames ("password
  spraying") does not buy more guesses from the same address. Only applied
  to globally routable addresses: a private/loopback address here means the
  API is seeing its own proxy or a shared NAT, and blocking it would lock
  out every learner behind it.

The lock doubles with every failure past the allowance (30 s, 1 min, 2 min
... capped at 15 min) and failures are forgotten after an hour, so nobody
is locked out permanently. A successful login clears that account's
counters; the per-address counter is deliberately left alone, so signing
into one's own account can't reset a spraying budget.

Keys are the submitted username (case-folded), whether or not the account
exists, so the 401/429 answers are identical for real and unknown
usernames. Only usernames, addresses and timestamps are held -- never a
password. State is in-process like the assistant's rate limit: production
runs a single uvicorn worker, and a restart (a deploy) only forgives.
Running several workers would need this moved to shared storage.
"""

from __future__ import annotations

import ipaddress
import math
import threading
import time

WINDOW_SECONDS = 60 * 60
BASE_LOCK_SECONDS = 30
MAX_LOCK_SECONDS = 15 * 60

PAIR_LIMIT = 5
ACCOUNT_LIMIT = 20
IP_LIMIT = 100

# Each key keeps at most this many timestamps. It must stay above every
# limit or that limit could never be reached; past a limit the lock itself
# keeps a key from growing much (locked attempts aren't recorded).
_MAX_PER_KEY = max(PAIR_LIMIT, ACCOUNT_LIMIT, IP_LIMIT) + 32
# A flood of distinct usernames/addresses must not grow memory without
# bound: past this, expired keys are swept, then the stalest dropped.
_MAX_KEYS = 100_000

LOCKED_DETAIL = "Too many sign-in attempts. Please wait a few minutes and try again."

_now = time.monotonic  # replaced in tests to move time without sleeping
_guard = threading.Lock()
_failures: dict[tuple[str, str], list[float]] = {}


def _account(username: str) -> str:
    return (username or "").strip().casefold()


def _is_global(ip: str | None) -> bool:
    if not ip:
        return False
    try:
        return ipaddress.ip_address(ip).is_global
    except ValueError:
        return False


def _keys(username: str, ip: str | None) -> list[tuple[tuple[str, str], int]]:
    account = _account(username)
    keys = [
        (("pair", f"{account}|{ip or '?'}"), PAIR_LIMIT),
        (("account", account), ACCOUNT_LIMIT),
    ]
    if _is_global(ip):
        keys.append((("ip", ip), IP_LIMIT))
    return keys


def _recent(key: tuple[str, str], now: float) -> list[float]:
    stamps = [t for t in _failures.get(key, ()) if now - t < WINDOW_SECONDS]
    if stamps:
        _failures[key] = stamps
    else:
        _failures.pop(key, None)
    return stamps


def _lock_seconds(count: int, limit: int) -> float:
    if count < limit:
        return 0.0
    return min(MAX_LOCK_SECONDS, BASE_LOCK_SECONDS * 2 ** (count - limit))


def retry_after(username: str, ip: str | None) -> int:
    """Seconds until a login for this username from this address may be
    attempted; 0 when it isn't locked."""
    now = _now()
    wait = 0.0
    with _guard:
        for key, limit in _keys(username, ip):
            stamps = _recent(key, now)
            if stamps:
                wait = max(wait, stamps[-1] + _lock_seconds(len(stamps), limit) - now)
    return max(0, math.ceil(wait))


def record_failure(username: str, ip: str | None) -> None:
    now = _now()
    with _guard:
        for key, _limit in _keys(username, ip):
            stamps = _recent(key, now)
            stamps.append(now)
            _failures[key] = stamps[-_MAX_PER_KEY:]
        if len(_failures) > _MAX_KEYS:
            _sweep(now)


def record_success(username: str, ip: str | None) -> None:
    account = _account(username)
    with _guard:
        _failures.pop(("pair", f"{account}|{ip or '?'}"), None)
        _failures.pop(("account", account), None)


def _sweep(now: float) -> None:
    for key in list(_failures):
        _recent(key, now)
    if len(_failures) > _MAX_KEYS:
        stalest = sorted(_failures, key=lambda k: _failures[k][-1])
        for key in stalest[: len(_failures) - _MAX_KEYS]:
            del _failures[key]


def reset() -> None:
    """Forget every counter (tests, and a manual escape hatch)."""
    with _guard:
        _failures.clear()
