"""Per-learner hourly budget for model calls made while grading.

Every Gemini call costs the shared quota (the free tier is ~20 requests a
day per model). The assistant, grammar lessons and Stories each had their
own per-learner cap, but Pet Teacher grading, detective-case verdicts, One
Sentence translations and voice evaluation called the model on every
request, so one scripted account could spend the quota for everyone.

Those calls now spend from one budget per learner. Past it nothing is
refused: the call runs on the deterministic offline path, exactly as on a
server without a key (wrap it in ai_client.offline_unless(spend(user.id))).
In-process, like the other limits: one uvicorn worker, a restart forgives.
"""

from __future__ import annotations

import threading
import time

CALLS_PER_HOUR = 150  # generous for real study, a wall for a runaway script

_now = time.monotonic  # replaced in tests
_guard = threading.Lock()
_calls: dict[int, list[float]] = {}


def spend(user_id: int) -> bool:
    """Record one model call for this learner; False once the hour's budget
    is used (the caller then stays offline and nothing is recorded)."""
    now = _now()
    with _guard:
        calls = [t for t in _calls.get(user_id, ()) if now - t < 3600]
        if len(calls) >= CALLS_PER_HOUR:
            _calls[user_id] = calls
            return False
        calls.append(now)
        _calls[user_id] = calls
        return True


def reset() -> None:
    with _guard:
        _calls.clear()
