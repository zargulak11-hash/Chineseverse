"""The one spaced-repetition rule (services/srs.py) every graded review
uses: FSRS-4.5 with its published default parameters.

Pure unit tests: a record and a learner are plain objects, so the
forgetting curve, each update rule, the relearning step after a miss, the
snake's flat (never compounding) memory bonus, seeding records reviewed
under the old schedule, and the mastery/status thresholds are pinned down
exactly."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.services import srs
from app.services.srs import apply_srs

SNAKE = SimpleNamespace(animal=SimpleNamespace(slug="snake"))
PLAIN = SimpleNamespace(animal=None)


def record(mastery=0.0, **kw):
    base = dict(mastery=mastery, times_seen=0, times_missed=0, status="new", next_review_at=None,
                last_reviewed_at=None, stability=None, difficulty=None)
    base.update(kw)
    return SimpleNamespace(**base)


def gap_days(rec):
    return (rec.next_review_at - rec.last_reviewed_at).total_seconds() / 86400


def age(rec, days):
    """Moves the record's last review `days` into the past (time passing)."""
    shift = timedelta(days=days)
    rec.last_reviewed_at -= shift
    rec.next_review_at -= shift


def close(a, b, tol=0.01):
    return abs(a - b) <= tol


# ---------------------------------------------------------------------------- the curve

def test_recall_is_ninety_percent_after_exactly_stability_days():
    for s in (0.5, 3.7, 40.0):
        assert close(srs.retrievability(s, s), 0.9, 1e-9)
        assert close(srs.interval_days(s), s, 1e-9)
    assert srs.retrievability(0, 5) == 1.0
    assert srs.retrievability(10, 5) < srs.retrievability(5, 5) < 1.0


def test_published_initial_values():
    assert [srs.W[g - 1] for g in (1, 2, 3, 4)] == [0.4872, 1.4003, 3.7145, 13.8206]
    assert close(srs.initial_difficulty(srs.GOOD), 5.1618, 1e-9)
    assert srs.initial_difficulty(srs.AGAIN) > srs.initial_difficulty(srs.GOOD) > srs.initial_difficulty(srs.EASY)
    assert 1.0 <= srs.initial_difficulty(srs.EASY) and srs.initial_difficulty(srs.AGAIN) <= 10.0


# ---------------------------------------------------------------------------- reviews

def test_a_first_right_answer_comes_back_after_good_stability():
    rec = record()
    apply_srs(rec, True, PLAIN)
    assert close(rec.stability, 3.7145, 1e-9) and close(rec.difficulty, 5.1618, 1e-9)
    assert close(gap_days(rec), 3.7145, 1e-3)
    assert rec.mastery == 10.0 and rec.times_seen == 1 and rec.status == "learning"


def test_each_review_on_time_grows_the_interval():
    rec = record()
    gaps = []
    for _ in range(6):
        apply_srs(rec, True, PLAIN)
        gaps.append(gap_days(rec))
        age(rec, gap_days(rec))  # reviewed exactly when due
    # Strictly longer each time until the 180-day cap (3.7, 14, 47, 140, 180...).
    assert all(b > a or close(b, 180, 1e-3) for a, b in zip(gaps, gaps[1:])), gaps
    assert gaps[1] > 2 * gaps[0] and close(max(gaps), 180, 1e-3)


def test_an_item_forgotten_often_grows_slower_than_an_easy_one():
    easy, hard = record(), record()
    apply_srs(easy, True, PLAIN)
    apply_srs(hard, False, PLAIN)
    for rec in (easy, hard):
        for _ in range(3):
            age(rec, max(gap_days(rec), 1))
            apply_srs(rec, True, PLAIN)
    assert hard.difficulty > easy.difficulty
    assert hard.stability < easy.stability


def test_recalling_later_than_due_is_stronger_evidence():
    on_time, late = record(), record()
    for rec in (on_time, late):
        apply_srs(rec, True, PLAIN)
    age(on_time, gap_days(on_time))
    age(late, gap_days(late) * 3)
    for rec in (on_time, late):
        apply_srs(rec, True, PLAIN)
    assert late.stability > on_time.stability


def test_a_miss_comes_back_in_six_hours_and_never_makes_memory_stronger():
    rec = record(mastery=40.0)
    apply_srs(rec, True, PLAIN)
    age(rec, gap_days(rec))
    s_before, d_before = rec.stability, rec.difficulty
    apply_srs(rec, False, PLAIN)
    assert close(gap_days(rec), 0.25, 1e-3)
    assert rec.stability <= s_before and rec.difficulty > d_before
    assert rec.mastery == 45.0 and rec.times_missed == 1 and rec.times_seen == 2


def test_same_day_reviews_do_not_inflate_stability():
    rec = record()
    apply_srs(rec, True, PLAIN)
    s = rec.stability
    apply_srs(rec, True, PLAIN)  # again, minutes later
    assert close(rec.stability, s, 1e-6)
    assert gap_days(rec) >= 1


def test_the_snakes_memory_bonus_is_flat_and_never_compounds():
    plain, snake = record(), record()
    for _ in range(4):
        apply_srs(plain, True, PLAIN)
        apply_srs(snake, True, SNAKE)
        # FSRS state is the same: the bonus only stretches the gap.
        assert close(snake.stability, plain.stability, 1e-9)
        assert close(gap_days(snake), gap_days(plain) * 2, 1e-3)
        g = gap_days(plain)
        age(plain, g)
        age(snake, g)


def test_intervals_are_capped():
    rec = record(stability=5000.0, difficulty=1.0, last_reviewed_at=datetime.utcnow() - timedelta(days=400),
                 next_review_at=datetime.utcnow())
    apply_srs(rec, True, PLAIN)
    assert close(gap_days(rec), 180, 1e-3)


# ---------------------------------------------------------------------------- old records

def test_a_record_from_the_old_schedule_is_seeded_from_it():
    now = datetime.utcnow()
    rec = record(mastery=70.0, status="reviewing", times_seen=6, times_missed=0,
                 last_reviewed_at=now - timedelta(days=8), next_review_at=now)  # an 8-day gap, due now
    apply_srs(rec, True, PLAIN)
    # Seeded S=8 recalled exactly at R=0.9, then grown by a success.
    assert rec.stability > 8 and close(rec.difficulty, srs.next_difficulty(srs.initial_difficulty(3), 3), 1e-9)
    missy = record(mastery=40.0, status="learning", times_seen=4, times_missed=2,
                   last_reviewed_at=now - timedelta(days=1), next_review_at=now)
    apply_srs(missy, True, PLAIN)
    assert missy.difficulty > rec.difficulty  # its own miss rate made it harder


def test_recall_probability_is_only_given_for_modelled_items():
    assert srs.recall_probability(record()) is None
    rec = record()
    apply_srs(rec, True, PLAIN)
    assert close(srs.recall_probability(rec), 1.0, 1e-3)
    age(rec, rec.stability)
    assert close(srs.recall_probability(rec), 0.9, 1e-3)


# ---------------------------------------------------------------------------- mastery

def test_mastery_stays_within_zero_and_one_hundred():
    low = record(mastery=3.0)
    apply_srs(low, False, PLAIN)
    high = record(mastery=98.0)
    apply_srs(high, True, PLAIN)
    assert low.mastery == 0.0 and high.mastery == 100.0


@pytest.mark.parametrize("mastery, status", [(0.0, "learning"), (54.9, "learning"), (55.0, "reviewing"),
                                            (84.9, "reviewing"), (85.0, "mastered"), (100.0, "mastered")])
def test_status_follows_mastery_thresholds(mastery, status):
    rec = record(mastery=mastery)
    apply_srs(rec, True, PLAIN, delta=0.0)
    assert rec.status == status


def test_a_custom_counter_and_delta_are_honoured():
    rec = record(times_written=2)
    apply_srs(rec, True, PLAIN, delta=25.0, counter="times_written")
    assert rec.times_written == 3 and rec.mastery == 25.0


def test_the_review_time_is_now():
    before = datetime.utcnow()
    rec = record()
    apply_srs(rec, True, PLAIN)
    assert before <= rec.last_reviewed_at <= datetime.utcnow()
