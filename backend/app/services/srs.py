"""Spaced repetition shared by every graded review (vocabulary, Hanzi
recognition, grammar, practice sessions) -- scheduled by FSRS.

When an item comes back is decided by FSRS-4.5 (Free Spaced Repetition
Scheduler, the algorithm Anki ships), with its published default
parameters (open-spaced-repetition/awesome-fsrs wiki, "The Algorithm").
Each record carries two numbers learned from ITS OWN history:

  stability   days until the chance of recalling it falls to 90%
  difficulty  1-10; rises when it is forgotten, settles when recalled

From them, R(t, S) = (1 + 19/81 * t/S) ** -0.5 is the probability of
recalling it t days after the last review, and the next review is set when
R would reach DESIRED_RETENTION (90%) -- for that target the interval is
exactly S days. A success grows S more when recall was harder (lower R) and
the item easier (lower D); a lapse shrinks it. This replaced a fixed
doubling (1, 2, 4 ... 30 days) that was the same for an easy word and one
forgotten five times.

Grading is pass/fail (Anki's two-button mode): a right answer is "Good",
a wrong one "Again". A miss also comes back after RELEARN_AFTER the same
day (a relearning step), whatever S became. The snake companion's memory
multiplier is still a flat bonus on the interval, never compounded.

Records reviewed before FSRS existed have no stability yet; their first
FSRS review seeds it from the interval the old schedule had given them (the
gap it had predicted they would survive) and seeds difficulty from their
own miss rate -- nothing is reset.

`mastery` (0-100) and `status` are unchanged: they are the learner-facing
progress, not the schedule. "Mastered" needs recall, not just recognition:
picking a word out of options -- or pressing "I know it" -- can push
mastery past 85, but a word or character (the records that have
`times_recalled`) only becomes "mastered" once it has also been produced
from memory in a typed question (services/recall.py, `recall=True`). A
record mastered before that rule existed is not demoted by a right answer.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from app import models
from app.services.gamification import memory_multiplier

# FSRS-4.5 default parameters w0..w16, digit for digit as published.
W = (0.4872, 1.4003, 3.7145, 13.8206, 5.1618, 1.2298, 0.8975, 0.031, 1.6474, 0.1367,
     1.0461, 2.1072, 0.0793, 0.3246, 1.587, 0.2272, 2.8755)
DECAY = -0.5
FACTOR = 19 / 81
DESIRED_RETENTION = 0.9
AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4
MAX_INTERVAL = timedelta(days=180)
MIN_INTERVAL = timedelta(days=1)  # a passed review never comes back the same day
RELEARN_AFTER = timedelta(hours=6)


def retrievability(elapsed_days: float, stability: float) -> float:
    """FSRS forgetting curve: the predicted probability of recall."""
    return (1 + FACTOR * max(0.0, elapsed_days) / stability) ** DECAY


def interval_days(stability: float, retention: float = DESIRED_RETENTION) -> float:
    return stability / FACTOR * (retention ** (1 / DECAY) - 1)


def _clamp_d(d: float) -> float:
    return min(10.0, max(1.0, d))


def initial_difficulty(grade: int) -> float:
    return _clamp_d(W[4] - (grade - 3) * W[5])


def next_difficulty(d: float, grade: int) -> float:
    # Linear step, then mean reversion towards D0(Good) so it cannot drift away.
    return _clamp_d(W[7] * initial_difficulty(GOOD) + (1 - W[7]) * (d - W[6] * (grade - 3)))


def stability_after_success(d: float, s: float, r: float, grade: int = GOOD) -> float:
    hard = W[15] if grade == HARD else 1.0
    easy = W[16] if grade == EASY else 1.0
    return s * (math.exp(W[8]) * (11 - d) * s ** -W[9] * (math.exp(W[10] * (1 - r)) - 1) * hard * easy + 1)


def stability_after_failure(d: float, s: float, r: float) -> float:
    # Forgetting never makes a memory MORE stable than it was (the same cap
    # the reference schedulers apply).
    return min(s, W[11] * d ** -W[12] * ((s + 1) ** W[13] - 1) * math.exp(W[14] * (1 - r)))


def _seed(rec) -> tuple[float, float] | None:
    """(stability, difficulty) for a record reviewed under the old doubling
    schedule: the gap it had been given, and its own miss rate. None for a
    record never reviewed (FSRS starts it from the first grade)."""
    if rec.last_reviewed_at is None or rec.next_review_at is None:
        return None
    gap_days = (rec.next_review_at - rec.last_reviewed_at).total_seconds() / 86400
    seen = (getattr(rec, "times_seen", None) or getattr(rec, "times_practiced", None) or 0)
    missed = rec.times_missed or 0
    miss_rate = missed / seen if seen else 0.0
    return max(0.25, gap_days), _clamp_d(initial_difficulty(GOOD) + 4 * miss_rate)


def _schedule(rec, correct: bool, now: datetime) -> timedelta:
    """Updates rec.stability / rec.difficulty by FSRS; returns the base
    interval until the next review (before the companion bonus)."""
    grade = GOOD if correct else AGAIN
    s, d = rec.stability, rec.difficulty
    if s is None or d is None:
        seeded = _seed(rec)
        if seeded is None:
            rec.stability, rec.difficulty = W[grade - 1], initial_difficulty(grade)
            return interval(rec.stability) if correct else RELEARN_AFTER
        s, d = seeded
    elapsed = (now - rec.last_reviewed_at).total_seconds() / 86400 if rec.last_reviewed_at else 0.0
    r = retrievability(elapsed, s)
    # Stability is updated from the difficulty the item HAD at this review
    # (as the reference optimizer does); difficulty moves after.
    rec.stability = stability_after_success(d, s, r) if correct else stability_after_failure(d, s, r)
    rec.difficulty = next_difficulty(d, grade)
    return interval(rec.stability) if correct else RELEARN_AFTER


def interval(stability: float) -> timedelta:
    return min(MAX_INTERVAL, max(MIN_INTERVAL, timedelta(days=interval_days(stability))))


def apply_srs(rec, correct: bool, user: models.User, delta: float = 10.0, counter: str = "times_seen",
              recall: bool = False) -> None:
    setattr(rec, counter, (getattr(rec, counter) or 0) + 1)
    now = datetime.utcnow()
    gated = hasattr(rec, "times_recalled")
    if correct and recall and gated:
        rec.times_recalled = (rec.times_recalled or 0) + 1

    if hasattr(rec, "stability"):
        gap = _schedule(rec, correct, now)
    else:
        # A record without FSRS columns (none in the app today): a fixed step.
        gap = MIN_INTERVAL if correct else RELEARN_AFTER
    if correct:
        rec.mastery = min(100.0, (rec.mastery or 0.0) + delta)
        rec.next_review_at = now + min(MAX_INTERVAL, gap) * memory_multiplier(user)
    else:
        rec.times_missed = (rec.times_missed or 0) + 1
        rec.mastery = max(0.0, (rec.mastery or 0.0) - delta * 0.5)
        rec.next_review_at = now + gap

    if rec.mastery >= 85 and gated and not (rec.times_recalled or 0) and rec.status != "mastered":
        rec.status = "reviewing"  # recognised, not yet recalled
    elif rec.mastery >= 85:
        rec.status = "mastered"
    elif rec.mastery >= 55:
        rec.status = "reviewing"
    else:
        rec.status = "learning"
    rec.last_reviewed_at = now


def recall_probability(rec, now: datetime | None = None) -> float | None:
    """FSRS's predicted chance of recalling `rec` right now, or None when it
    has no FSRS memory yet (never reviewed since FSRS) -- never a guess."""
    if getattr(rec, "stability", None) is None or rec.last_reviewed_at is None:
        return None
    now = now or datetime.utcnow()
    return retrievability((now - rec.last_reviewed_at).total_seconds() / 86400, rec.stability)


# A word or character the learner already knew (reviewing or mastered) whose
# scheduled review is this late is "slipping": the schedule chose that day
# because recall was expected to fade around then. It is not a new status --
# nothing is downgraded or reset -- only a reading of the stored schedule, so
# the learner sees what they are losing before it is lost.
SLIP_AFTER = timedelta(days=3)


def is_slipping(rec, now: datetime | None = None) -> bool:
    now = now or datetime.utcnow()
    return bool(
        rec is not None
        and rec.status in ("reviewing", "mastered")
        and rec.next_review_at is not None
        and now - rec.next_review_at >= SLIP_AFTER
    )
