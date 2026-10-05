"""Learning activity reaches the Progress activity card: every learning
action logs an ActivityEvent AND counts the day toward the streak, day
boundaries use the same UTC date the events are stored in, and a broken
streak is shown as broken."""

from datetime import datetime, timedelta

import pytest

from app import models
from app.database import SessionLocal
from app.services.activity import log_activity
from helpers import expect, register, unique_name


def streak_row(uid):
    with SessionLocal() as db:
        rows = db.query(models.UserStreak).filter_by(user_id=uid).all()
        assert len(rows) <= 1, f"duplicate streak rows for user {uid}"
        return rows[0] if rows else None


def events(uid):
    with SessionLocal() as db:
        return [e.action_type for e in db.query(models.ActivityEvent).filter_by(user_id=uid).order_by(models.ActivityEvent.id)]


def drop_streak(uid):
    # Registration creates an empty row; remove it to exercise the
    # "no streak row yet" path (older accounts / first request).
    with SessionLocal() as db:
        db.query(models.UserStreak).filter_by(user_id=uid).delete()
        db.commit()


def practice_round(client, h, **body):
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"size": 4, **body})
    for i, q in enumerate(s["questions"]):
        expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
               json={"index": i, "choice_id": q["options"][0]["id"], "response_ms": 1500})
    return expect(client, "post", f"/api/practice/sessions/{s['id']}/complete", 200, headers=h)


def first_hanzi(client, h):
    return expect(client, "get", "/api/hanzi?hsk_level=1", 200, headers=h)[0]


def self_check(client, h, hz):
    expect(client, "post", f"/api/hanzi/{hz['id']}/review", 200, headers=h, json={"correct": True})


@pytest.fixture
def today():
    return datetime.utcnow().date()


def test_first_ever_hanzi_self_check_starts_the_streak(client, today):
    # It used to create a row with current_streak=0.
    uid, h = register(client, unique_name())
    drop_streak(uid)
    self_check(client, h, first_hanzi(client, h))
    s = streak_row(uid)
    assert s and s.current_streak == 1 and s.total_active_days == 1 and s.last_active_date == today, vars(s)
    assert events(uid) == ["hanzi_review"]


def test_first_practice_answer_creates_exactly_one_streak_row(client):
    # touch_streak runs twice in one request (practice + log_activity).
    uid, h = register(client, unique_name())
    drop_streak(uid)
    s0 = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "vocab", "hsk_level": 1, "size": 4})
    q0 = s0["questions"][0]
    expect(client, "post", f"/api/practice/sessions/{s0['id']}/answer", 200, headers=h,
           json={"index": 0, "choice_id": q0["options"][0]["id"], "response_ms": 1500})
    s = streak_row(uid)
    assert s.current_streak == 1 and s.total_active_days == 1, vars(s)


def test_many_activity_types_on_one_day_count_the_streak_once(client, today):
    uid, h = register(client, unique_name())
    expect(client, "get", "/api/dashboard", 200, headers=h)  # creates the (empty) streak row like the app does
    with SessionLocal() as db:
        xp_before = db.get(models.User, uid).total_xp or 0
    practice_round(client, h, source="vocab", hsk_level=1)
    practice_round(client, h, source="hanzi", hsk_level=1)
    self_check(client, h, first_hanzi(client, h))
    practice_round(client, h, source="grammar", hsk_level=1)
    lesson = next(l for l in expect(client, "get", "/api/lessons?hsk_level=1", 200, headers=h)
                  if expect(client, "get", f"/api/lessons/{l['id']}/items", 200, headers=h)["vocab"])
    practice_round(client, h, source="lesson", lesson_id=lesson["id"])
    kinds = set(events(uid))
    assert {"practice_answer", "hanzi_review"} <= kinds, kinds
    s = streak_row(uid)
    assert s.current_streak == 1 and s.total_active_days == 1 and s.last_active_date == today, vars(s)
    n = len(events(uid))
    a = expect(client, "get", "/api/analytics/activity", 200, headers=h)
    assert a["days"][-1]["date"] == today.isoformat(), a["days"][-1]
    assert a["days"][-1]["actions"] == n == a["today_actions"], (a["days"][-1], n)
    assert a["streak"]["current_streak"] == 1
    sections = {x["section"] for x in a["sections"]}
    assert {"practice", "hanzi"} <= sections, sections
    # XP still comes only from the existing rules (practice correct answers etc.)
    with SessionLocal() as db:
        assert (db.get(models.User, uid).total_xp or 0) >= xp_before


def test_yesterday_and_today_make_a_two_day_streak(client, today):
    uid, h = register(client, unique_name())
    hz = first_hanzi(client, h)
    yesterday = today - timedelta(days=1)
    with SessionLocal() as db:
        user = db.get(models.User, uid)
        log_activity(db, user, "hanzi_write", when=datetime.utcnow() - timedelta(days=1))
        # log_activity touched "today"; restore the backdated state
        user.streak.last_active_date = yesterday
        user.streak.current_streak = 1
        user.streak.longest_streak = 1
        user.streak.total_active_days = 1
        db.commit()
    self_check(client, h, hz)
    s = streak_row(uid)
    assert s.current_streak == 2 and s.longest_streak == 2 and s.total_active_days == 2, vars(s)
    a = expect(client, "get", "/api/analytics/activity", 200, headers=h)
    assert a["days"][-2]["date"] == yesterday.isoformat() and a["days"][-2]["actions"] == 1, a["days"][-2]
    assert a["days"][-1]["actions"] == 1, a["days"][-1]
    assert a["best_streak_past_year"] == 2 and a["streak"]["current_streak"] == 2


def test_a_broken_streak_reads_zero_without_writing_and_restarts_at_one(client, today):
    uid, h = register(client, unique_name())
    with SessionLocal() as db:
        st = db.query(models.UserStreak).filter_by(user_id=uid).one()
        st.last_active_date = today - timedelta(days=3)
        st.current_streak = 5
        st.longest_streak = 5
        db.commit()
    assert expect(client, "get", "/api/analytics/activity", 200, headers=h)["streak"]["current_streak"] == 0
    dash = expect(client, "get", "/api/dashboard", 200, headers=h)
    assert dash["streak"]["current_streak"] == 0 and dash["streak"]["longest_streak"] == 5, dash["streak"]
    assert streak_row(uid).current_streak == 5, "reading the card must not write the streak"
    self_check(client, h, first_hanzi(client, h))
    s = streak_row(uid)
    assert s.current_streak == 1 and s.longest_streak == 5, vars(s)


def test_activity_is_scoped_to_the_signed_in_learner(client):
    uid, h = register(client, unique_name())
    _, busy = register(client, unique_name())
    practice_round(client, busy, source="vocab", hsk_level=1)
    self_check(client, h, first_hanzi(client, h))
    a = expect(client, "get", "/api/analytics/activity", 200, headers=h)
    assert a["today_actions"] == len(events(uid)) == 1, a["today_actions"]
    expect(client, "get", "/api/analytics/activity", 401)
