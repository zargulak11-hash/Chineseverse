"""The daily streak counts real learning days on the learner's own calendar.

Regression for "🔥 0 days" in the header: the streak counted UTC days (a
Dushanbe learner's 01:00 session landed on the day before, so four
consecutive local days read as a broken streak), choosing a companion or
pinging the API counted as learning, and a day the counter got wrong stayed
wrong. Now a day counts only through an ActivityEvent (a real learning
action) and the run is recomputed from that log in the learner's time zone,
which the browser sends as X-Timezone.

The clock is frozen per "day" so whole days can be walked through the real
API: the same requests the app makes, the same rows they persist."""

from datetime import date, datetime, timedelta

import pytest

from app import models
from app.database import SessionLocal
from app.services import activity, gamification
from app.services.activity import log_activity
from helpers import expect, register, unique_name

DUSHANBE = {"X-Timezone": "Asia/Dushanbe"}  # UTC+5, no DST


@pytest.fixture
def clock(monkeypatch):
    """Set the UTC "now" the streak and the activity log see."""
    state = {"now": datetime(2026, 3, 2, 9, 0)}

    class Frozen(datetime):
        @classmethod
        def utcnow(cls):
            return state["now"]

    monkeypatch.setattr(gamification, "datetime", Frozen)
    monkeypatch.setattr(activity, "datetime", Frozen)

    def set_now(value: datetime) -> None:
        state["now"] = value

    return set_now


def learn(client, h, extra=None):
    """One real, server-graded learning action: answer a practice question."""
    headers = {**h, **(extra or {})}
    s = expect(client, "post", "/api/practice/sessions", 201, headers=headers,
               json={"source": "vocab", "hsk_level": 1, "size": 4})
    q = s["questions"][0]
    expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=headers,
           json={"index": 0, "choice_id": q["options"][0]["id"], "response_ms": 1500})


def header_streak(client, h, extra=None):
    """What the header's flame chip shows: dashboard.streak.current_streak."""
    return expect(client, "get", "/api/dashboard", 200, headers={**h, **(extra or {})})["streak"]


def stored(uid):
    with SessionLocal() as db:
        s = db.query(models.UserStreak).filter_by(user_id=uid).one()
        return s.current_streak, s.longest_streak, s.total_active_days, s.last_active_date


def event_days(uid):
    with SessionLocal() as db:
        return sorted({e.created_at.date() for e in db.query(models.ActivityEvent).filter_by(user_id=uid)})


def test_a_learning_action_is_persisted_and_the_header_shows_it_after_a_refresh(client, clock):
    clock(datetime(2026, 3, 2, 9, 0))
    uid, h = register(client, unique_name("streak"))
    assert header_streak(client, h)["current_streak"] == 0
    learn(client, h)
    assert event_days(uid) == [date(2026, 3, 2)], "the learning action is stored in the activity log"
    assert stored(uid) == (1, 1, 1, date(2026, 3, 2))
    # A page refresh is a fresh GET of everything the header and Profile read.
    for _ in range(2):
        assert header_streak(client, h)["current_streak"] == 1
        assert expect(client, "get", "/api/me", 200, headers=h)["streak"]["current_streak"] == 1
    assert expect(client, "get", "/api/analytics/activity", 200, headers=h)["streak"]["current_streak"] == 1


def test_opening_the_app_is_not_a_learning_day(client, clock):
    clock(datetime(2026, 3, 2, 9, 0))
    uid, h = register(client, unique_name("streak"))
    for _ in range(3):
        header_streak(client, h)
        expect(client, "get", "/api/me", 200, headers=h)
    ping = expect(client, "post", "/api/me/ping", 200, headers=h)
    assert ping == {"streak": ping["streak"], "new_day": False} and ping["streak"]["current_streak"] == 0
    expect(client, "post", "/api/me/animal", 200, headers=h, json={"animal_id": 1})
    # Opening Practice builds a round; leaving it unanswered is not learning.
    expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "vocab", "hsk_level": 1, "size": 4})
    assert event_days(uid) == []
    assert stored(uid)[0] == 0 and header_streak(client, h)["current_streak"] == 0


def test_consecutive_days_grow_the_streak_and_repeat_actions_count_a_day_once(client, clock):
    clock(datetime(2026, 3, 2, 9, 0))
    uid, h = register(client, unique_name("streak"))
    for n, day in enumerate((2, 3, 4), start=1):
        clock(datetime(2026, 3, day, 9, 0))
        learn(client, h)
        clock(datetime(2026, 3, day, 15, 0))
        learn(client, h)  # a second session the same day changes nothing
        assert header_streak(client, h)["current_streak"] == n
    assert stored(uid) == (3, 3, 3, date(2026, 3, 4))
    # The next morning, before learning, yesterday's run is still alive.
    clock(datetime(2026, 3, 5, 8, 0))
    assert header_streak(client, h)["current_streak"] == 3


def test_a_missed_day_breaks_the_streak_and_the_next_learning_day_starts_over(client, clock):
    clock(datetime(2026, 3, 2, 9, 0))
    uid, h = register(client, unique_name("streak"))
    for day in (2, 3):
        clock(datetime(2026, 3, day, 9, 0))
        learn(client, h)
    clock(datetime(2026, 3, 5, 9, 0))  # March 4th missed
    s = header_streak(client, h)
    assert s["current_streak"] == 0 and s["longest_streak"] == 2, s
    assert stored(uid)[0] == 2, "reading the header must not write the streak"
    learn(client, h)
    s = header_streak(client, h)
    assert s["current_streak"] == 1 and s["longest_streak"] == 2 and s["total_active_days"] == 3, s


def test_days_follow_the_learners_time_zone_not_utc(client, clock):
    # The real history that showed the bug: evenings and a 01:38 session in
    # Dushanbe. In UTC the 25th is empty (20:38 UTC is still the 24th), so
    # the streak broke; in the learner's calendar it is four days running.
    clock(datetime(2026, 9, 23, 11, 0))
    uid, h = register(client, unique_name("streak"))
    for at in (datetime(2026, 9, 23, 11, 56), datetime(2026, 9, 24, 16, 30),
               datetime(2026, 9, 24, 20, 38), datetime(2026, 9, 26, 1, 33)):
        clock(at)
        learn(client, h, DUSHANBE)
    with SessionLocal() as db:
        assert db.get(models.User, uid).timezone == "Asia/Dushanbe", "the browser's zone is remembered"
    assert stored(uid) == (4, 4, 4, date(2026, 9, 26))
    clock(datetime(2026, 9, 26, 12, 0))
    a = expect(client, "get", "/api/analytics/activity", 200, headers={**h, **DUSHANBE})
    assert a["streak"]["current_streak"] == 4
    assert [d["date"] for d in a["days"][-4:] if d["actions"]] == ["2026-09-23", "2026-09-24", "2026-09-25", "2026-09-26"]


def test_the_local_day_boundary_decides_today(client, clock):
    clock(datetime(2026, 3, 2, 9, 0))
    uid, h = register(client, unique_name("streak"))
    # 21:00 UTC on the 2nd is 02:00 on the 3rd in Dushanbe, and 04:00 UTC
    # on the 3rd (09:00 local) is the same local day: one day, not two.
    clock(datetime(2026, 3, 2, 21, 0))
    learn(client, h, DUSHANBE)
    clock(datetime(2026, 3, 3, 4, 0))
    learn(client, h, DUSHANBE)
    assert stored(uid) == (1, 1, 1, date(2026, 3, 3))
    # 19:30 UTC on the 3rd is already 00:30 on the 4th there: a new day.
    clock(datetime(2026, 3, 3, 19, 30))
    assert header_streak(client, h, DUSHANBE)["current_streak"] == 1  # yesterday's run, still alive
    learn(client, h, DUSHANBE)
    assert header_streak(client, h, DUSHANBE)["current_streak"] == 2
    # A whole local day with nothing: at 19:30 UTC on the 5th it is the
    # 6th in Dushanbe, so the 5th was missed and the streak reads 0.
    clock(datetime(2026, 3, 5, 19, 30))
    assert header_streak(client, h, DUSHANBE)["current_streak"] == 0


def test_without_a_known_zone_days_stay_utc_and_junk_zones_are_ignored(client, clock):
    clock(datetime(2026, 3, 2, 23, 30))
    uid, h = register(client, unique_name("streak"))
    learn(client, h, {"X-Timezone": "Not/AZone"})
    clock(datetime(2026, 3, 3, 0, 30))
    learn(client, h, {"X-Timezone": "../../etc/passwd"})
    with SessionLocal() as db:
        assert db.get(models.User, uid).timezone is None
    assert stored(uid) == (2, 2, 2, date(2026, 3, 3))


def test_existing_history_is_kept_and_rebuilt_from_the_log(client, clock):
    clock(datetime(2026, 3, 10, 9, 0))
    uid, h = register(client, unique_name("streak"))
    with SessionLocal() as db:
        user = db.get(models.User, uid)
        for day in (6, 7, 9):  # real logged days; the counter below lost one
            log_activity(db, user, "hanzi_review", when=datetime(2026, 3, day, 9, 0))
        st = user.streak
        st.current_streak, st.longest_streak, st.total_active_days = 1, 7, 12  # older history
        st.last_active_date = date(2026, 3, 9)
        db.commit()
        events_before = db.query(models.ActivityEvent).filter_by(user_id=uid).count()
    learn(client, h)
    current, longest, total, last = stored(uid)
    assert (current, last) == (2, date(2026, 3, 10)), "the run is rebuilt from the log (9th + 10th)"
    assert longest == 7 and total == 13, "earlier history is never lowered"
    with SessionLocal() as db:
        assert db.query(models.ActivityEvent).filter_by(user_id=uid).count() == events_before + 1


def test_streak_helpers_on_fixed_dates():
    dushanbe = models.User(timezone="Asia/Dushanbe")
    utc = models.User(timezone=None)
    late = datetime(2026, 9, 24, 20, 38)
    assert gamification.local_date(dushanbe, late) == date(2026, 9, 25)
    assert gamification.local_date(utc, late) == date(2026, 9, 24)
    assert gamification.local_day_start(dushanbe, date(2026, 9, 25)) == datetime(2026, 9, 24, 19, 0)
    days = {date(2026, 3, d) for d in (1, 2, 3, 5, 6)}
    assert gamification._longest_run(days) == 3 and gamification._longest_run(set()) == 0
    assert gamification._run_ending(days, date(2026, 3, 6)) == 2
    assert gamification.valid_timezone("Asia/Dushanbe") == "Asia/Dushanbe"
    assert gamification.valid_timezone("") is None and gamification.valid_timezone("x" * 65) is None
    assert gamification.valid_timezone("Mars/Olympus") is None
