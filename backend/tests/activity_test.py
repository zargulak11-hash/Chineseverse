"""Learning activity reaches the Progress activity card: every learning
action logs an ActivityEvent AND counts the day toward the streak, day
boundaries use the same UTC date the events are stored in, and a broken
streak is shown as broken."""

import os
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/activity.db"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services.activity import log_activity  # noqa: E402


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, f"{method.upper()} {url} -> {resp.status_code} (expected {expected}): {resp.text}"
    return resp.json() if resp.content else None


def register(client, name):
    data = expect(client, "post", "/api/auth/register", 201,
                  json={"username": name, "email": f"{name}@example.com", "password": "secret1"})
    return data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}


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


today = datetime.utcnow().date()

with TestClient(app) as client:
    # --- a Hanzi self-check as the very first action (no streak row yet)
    # starts the streak; it used to create a row with current_streak=0.
    uid, h = register(client, "firsthanzi")
    drop_streak(uid)
    first_hz = expect(client, "get", "/api/hanzi?hsk_level=1", 200, headers=h)[0]
    expect(client, "post", f"/api/hanzi/{first_hz['id']}/review", 200, headers=h, json={"correct": True})
    s = streak_row(uid)
    assert s and s.current_streak == 1 and s.total_active_days == 1 and s.last_active_date == today, vars(s)
    assert events(uid) == ["hanzi_review"]
    print("[PASS] a first-ever Hanzi self-check logs activity and starts the streak at 1")

    # --- first action = practice answer with no streak row: touch_streak runs
    # twice in one request (practice + log_activity) without a duplicate row.
    uid2, h2 = register(client, "firstpractice")
    drop_streak(uid2)
    s0 = expect(client, "post", "/api/practice/sessions", 201, headers=h2, json={"source": "vocab", "hsk_level": 1, "size": 4})
    q0 = s0["questions"][0]
    expect(client, "post", f"/api/practice/sessions/{s0['id']}/answer", 200, headers=h2,
           json={"index": 0, "choice_id": q0["options"][0]["id"], "response_ms": 1500})
    s = streak_row(uid2)
    assert s.current_streak == 1 and s.total_active_days == 1, vars(s)
    print("[PASS] first practice answer creates exactly one streak row")

    # --- several activity types on one day: all logged, streak counted once
    uid, h = register(client, "manytypes")
    expect(client, "get", "/api/dashboard", 200, headers=h)  # creates the (empty) streak row like the app does
    with SessionLocal() as db:
        xp_before = db.get(models.User, uid).total_xp or 0
    practice_round(client, h, source="vocab", hsk_level=1)
    practice_round(client, h, source="hanzi", hsk_level=1)
    hz = expect(client, "get", "/api/hanzi?hsk_level=1", 200, headers=h)[0]
    expect(client, "post", f"/api/hanzi/{hz['id']}/review", 200, headers=h, json={"correct": True})
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
    print(f"[PASS] {len(kinds)} activity types on one day -> {n} events on today's cell, streak counted once")

    # --- previous day + consecutive days
    with SessionLocal() as db:
        user = db.get(models.User, uid)
        yesterday = today - timedelta(days=1)
        user.streak.last_active_date = yesterday
        user.streak.current_streak = 1
        user.streak.longest_streak = 1
        user.streak.total_active_days = 1
        db.query(models.ActivityEvent).filter_by(user_id=uid).delete()
        log_activity(db, user, "hanzi_write", when=datetime.utcnow() - timedelta(days=1))
        user.streak.last_active_date = yesterday  # log_activity touched "today"; restore the backdated state
        user.streak.current_streak = 1
        user.streak.total_active_days = 1
        db.commit()
    expect(client, "post", f"/api/hanzi/{hz['id']}/review", 200, headers=h, json={"correct": True})
    s = streak_row(uid)
    assert s.current_streak == 2 and s.longest_streak == 2 and s.total_active_days == 2, vars(s)
    a = expect(client, "get", "/api/analytics/activity", 200, headers=h)
    assert a["days"][-2]["date"] == yesterday.isoformat() and a["days"][-2]["actions"] == 1, a["days"][-2]
    assert a["days"][-1]["actions"] == 1, a["days"][-1]
    assert a["best_streak_past_year"] == 2 and a["streak"]["current_streak"] == 2
    print("[PASS] yesterday + today show as two cells and a 2-day streak")

    # --- a broken streak shows as broken until the next action restarts it
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
    expect(client, "post", f"/api/hanzi/{hz['id']}/review", 200, headers=h, json={"correct": True})
    s = streak_row(uid)
    assert s.current_streak == 1 and s.longest_streak == 5, vars(s)
    print("[PASS] a streak broken by missed days reads 0 (no write) and restarts at 1 on the next action")

    # --- each user only sees their own activity
    a2 = expect(client, "get", "/api/analytics/activity", 200, headers=h2)
    assert a2["today_actions"] == len(events(uid2)) == 1, a2["today_actions"]
    expect(client, "get", "/api/analytics/activity", 401)
    print("[PASS] activity is scoped to the signed-in user")

print("ALL ACTIVITY TESTS PASSED")
