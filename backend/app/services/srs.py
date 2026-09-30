"""Spaced-repetition update shared by every graded review (vocabulary,
Hanzi recognition, grammar, practice sessions).

Correct: mastery rises by `delta` and the next review roughly doubles the
previous gap (capped at 30 days; the snake companion's memory multiplier is
a flat bonus on top, never compounded). Wrong: mastery drops by half of
`delta` and the item comes back in 6 hours.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app import models
from app.services.gamification import memory_multiplier


def apply_srs(rec, correct: bool, user: models.User, delta: float = 10.0, counter: str = "times_seen") -> None:
    setattr(rec, counter, (getattr(rec, counter) or 0) + 1)
    now = datetime.utcnow()
    if correct:
        rec.mastery = min(100.0, (rec.mastery or 0.0) + delta)
        multiplier = memory_multiplier(user)
        prev_interval = (
            rec.next_review_at - rec.last_reviewed_at
            if rec.next_review_at and rec.last_reviewed_at
            else None
        )
        # Undo the previous step's multiplier before doubling, so it stays a
        # flat bonus instead of compounding into an ever-growing one.
        prev_base = prev_interval / multiplier if prev_interval and prev_interval.total_seconds() > 0 else None
        base = prev_base * 2 if prev_base else timedelta(days=1)
        rec.next_review_at = now + min(timedelta(days=30), base) * multiplier
    else:
        rec.times_missed = (rec.times_missed or 0) + 1
        rec.mastery = max(0.0, (rec.mastery or 0.0) - delta * 0.5)
        rec.next_review_at = now + timedelta(hours=6)

    if rec.mastery >= 85:
        rec.status = "mastered"
    elif rec.mastery >= 55:
        rec.status = "reviewing"
    else:
        rec.status = "learning"
    rec.last_reviewed_at = now
