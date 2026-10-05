"""The one spaced-repetition rule (services/srs.py) every graded review uses.

Pure unit tests: a record and a learner are plain objects, so each rule --
the doubling gap, the 30-day cap, the snake's flat (never compounding)
memory bonus, the 6-hour retry after a miss, the mastery bounds and the
status thresholds -- is pinned down exactly."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.services.srs import apply_srs

SNAKE = SimpleNamespace(animal=SimpleNamespace(slug="snake"))
PLAIN = SimpleNamespace(animal=None)


def record(mastery=0.0):
    return SimpleNamespace(mastery=mastery, times_seen=0, times_missed=0, status="new",
                           next_review_at=None, last_reviewed_at=None)


def gap(rec):
    return rec.next_review_at - rec.last_reviewed_at


def review(rec, correct, user=PLAIN, delta=10.0):
    apply_srs(rec, correct, user, delta)
    return rec


def close(a, b):
    return abs((a - b).total_seconds()) < 2


def test_a_first_correct_answer_schedules_tomorrow():
    rec = review(record(), True)
    assert close(gap(rec), timedelta(days=1))
    assert rec.mastery == 10.0 and rec.times_seen == 1 and rec.status == "learning"


def test_each_correct_answer_doubles_the_gap_up_to_thirty_days():
    rec = record()
    gaps = []
    for _ in range(8):
        review(rec, True)
        gaps.append(round(gap(rec) / timedelta(days=1)))
    assert gaps == [1, 2, 4, 8, 16, 30, 30, 30]


def test_the_snakes_memory_bonus_is_flat_and_never_compounds():
    plain, snake = record(), record()
    for _ in range(5):
        review(plain, True)
        review(snake, True, SNAKE)
        assert close(gap(snake), gap(plain) * 2), (gap(snake), gap(plain))
    # Past the cap the bonus still applies once on top of 30 days.
    for _ in range(3):
        review(snake, True, SNAKE)
    assert close(gap(snake), timedelta(days=60))


def test_a_miss_brings_the_item_back_in_six_hours_and_costs_half_a_step():
    rec = record(mastery=40.0)
    review(rec, False)
    assert close(gap(rec), timedelta(hours=6))
    assert rec.mastery == 35.0 and rec.times_missed == 1 and rec.times_seen == 1
    # After a miss the schedule climbs back from the short 6-hour gap
    # (doubling it each time), never jumping back to the old long one.
    recovery = []
    for _ in range(3):
        review(rec, True)
        recovery.append(gap(rec))
    assert all(close(g, w) for g, w in zip(recovery, (timedelta(hours=12), timedelta(days=1), timedelta(days=2))))


def test_mastery_stays_within_zero_and_one_hundred():
    low = review(record(mastery=3.0), False)
    high = review(record(mastery=98.0), True)
    assert low.mastery == 0.0 and high.mastery == 100.0


@pytest.mark.parametrize("mastery, status", [(0.0, "learning"), (54.9, "learning"), (55.0, "reviewing"),
                                            (84.9, "reviewing"), (85.0, "mastered"), (100.0, "mastered")])
def test_status_follows_mastery_thresholds(mastery, status):
    rec = record(mastery=mastery)
    apply_srs(rec, True, PLAIN, delta=0.0)
    assert rec.status == status


def test_a_custom_counter_and_delta_are_honoured():
    rec = SimpleNamespace(mastery=0.0, times_written=2, times_missed=0, status="new",
                          next_review_at=None, last_reviewed_at=None)
    apply_srs(rec, True, PLAIN, delta=25.0, counter="times_written")
    assert rec.times_written == 3 and rec.mastery == 25.0


def test_the_review_time_is_now():
    before = datetime.utcnow()
    rec = review(record(), True)
    assert before <= rec.last_reviewed_at <= datetime.utcnow()
