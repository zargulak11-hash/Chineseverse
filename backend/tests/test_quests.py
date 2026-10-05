"""Daily quests (services/gamification.py, routers/quests.py): one stable set
of three per learner per day, progress only from the matching activity,
and a reward that is paid exactly once -- even for two claims at the same
instant (a double click, two tabs)."""

import threading

import pytest

from app import models
from app.database import SessionLocal
from app.routers.quests import claim_quest
from app.services.gamification import progress_quests
from fastapi import HTTPException
from helpers import expect, register, unique_name


@pytest.fixture
def learner(client):
    uid, h = register(client, unique_name("quester"))
    return uid, h


def today(client, h, locale=None):
    headers = {**h, "X-Locale": locale} if locale else h
    return expect(client, "get", "/api/quests/today", 200, headers=headers)


def complete(quest_id):
    """Test setup: the quest's activity was done (progress has its own test)."""
    with SessionLocal() as db:
        q = db.get(models.DailyQuest, quest_id)
        q.progress, q.completed = q.target, True
        db.commit()


def balance(uid):
    with SessionLocal() as db:
        u = db.get(models.User, uid)
        return u.total_xp, u.coins


def test_a_learner_gets_one_stable_set_of_three_quests_a_day(client, learner):
    _, h = learner
    first = today(client, h)
    assert len(first) == 3 and len({q["quest_type"] for q in first}) == 3
    assert all(q["progress"] == 0 and not q["completed"] and not q["claimed"] for q in first)
    assert all(q["target"] >= 1 and q["reward_xp"] > 0 for q in first)
    # Asking again (another page, a reload) never rolls a new set.
    assert [q["id"] for q in today(client, h)] == [q["id"] for q in first]
    expect(client, "get", "/api/quests/today", 401)


def test_quest_titles_follow_the_learners_language(client, learner):
    _, h = learner
    en = {q["id"]: q["title"] for q in today(client, h)}
    ru = {q["id"]: q["title"] for q in today(client, h, "ru")}
    assert en.keys() == ru.keys() and all(en[k] != ru[k] for k in en), (en, ru)


def test_progress_comes_only_from_the_matching_activity_and_stops_at_the_target(client, learner):
    uid, h = learner
    quest = today(client, h)[0]
    _, other = register(client, unique_name("quest_other"))
    other_quest = today(client, other)
    with SessionLocal() as db:
        user = db.get(models.User, uid)
        unrelated = next(t for t in ("vocab", "lesson", "case", "duel", "speaking", "listening")
                         if t not in {q["quest_type"] for q in today(client, h)})
        progress_quests(db, user, unrelated, amount=5)
        db.commit()
        assert db.get(models.DailyQuest, quest["id"]).progress == 0, "another activity type moved this quest"
        for _ in range(quest["target"] + 3):
            progress_quests(db, user, quest["quest_type"])
        db.commit()
        row = db.get(models.DailyQuest, quest["id"])
        assert row.progress == quest["target"] and row.completed and not row.claimed
    # Another learner's quests never move.
    assert today(client, other) == other_quest


def test_claiming_pays_the_reward_once(client, learner):
    uid, h = learner
    quest = today(client, h)[0]
    expect(client, "post", f"/api/quests/{quest['id']}/claim", 409, headers=h)  # not completed yet
    complete(quest["id"])
    xp0, coins0 = balance(uid)
    claimed = expect(client, "post", f"/api/quests/{quest['id']}/claim", 200, headers=h)
    assert claimed["claimed"] is True
    assert balance(uid) == (xp0 + quest["reward_xp"], coins0 + quest["reward_coins"])
    body = expect(client, "post", f"/api/quests/{quest['id']}/claim", 409, headers=h)
    assert body["detail"] == "Quest already claimed"
    assert balance(uid) == (xp0 + quest["reward_xp"], coins0 + quest["reward_coins"])


def test_another_learners_quest_is_a_404_and_nothing_is_paid(client, learner):
    uid, h = learner
    quest = today(client, h)[0]
    complete(quest["id"])
    oid, other = register(client, unique_name("quest_thief"))
    before = balance(oid)
    expect(client, "post", f"/api/quests/{quest['id']}/claim", 404, headers=other)
    expect(client, "post", "/api/quests/999999/claim", 404, headers=other)
    expect(client, "post", f"/api/quests/{quest['id']}/claim", 401)
    assert balance(oid) == before
    with SessionLocal() as db:
        assert db.get(models.DailyQuest, quest["id"]).claimed is False


def test_two_simultaneous_claims_pay_once(client, learner):
    uid, h = learner
    quest = today(client, h)[0]
    complete(quest["id"])
    xp0, coins0 = balance(uid)
    barrier = threading.Barrier(4)
    results = []

    def claim():
        # Each thread is its own request: own session, same quest.
        with SessionLocal() as db:
            user = db.get(models.User, uid)
            barrier.wait()
            try:
                claim_quest(quest["id"], user=user, db=db, locale="en")
                results.append("ok")
            except HTTPException as exc:
                results.append(exc.status_code)
            except Exception as exc:  # e.g. SQLite "database is locked" under contention
                results.append(type(exc).__name__)

    threads = [threading.Thread(target=claim) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count("ok") == 1, results
    assert all(r in (409, "OperationalError") for r in results if r != "ok"), results
    assert balance(uid) == (xp0 + quest["reward_xp"], coins0 + quest["reward_coins"])
