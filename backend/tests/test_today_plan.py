"""Today's plan is built from real records only.

  * a brand-new learner gets ONE task (the first foundation step), nothing
    done, zero rounds/words/minutes -- no invented activity;
  * due reviews add a review task with the real count (not doubled -- the
    journey used to count every due item twice), and it is ticked off only
    after a review round was really finished today;
  * the weakest PRACTISED skill gets a task with the right place to practise;
    an unpractised skill never does;
  * the assistant's context carries the same plan.
"""

from datetime import datetime, timedelta

import pytest

from app import models
from app.database import SessionLocal
from app.routers import assistant as assistant_router
from helpers import expect, register, unique_name


def today(client, h):
    return expect(client, "get", "/api/journey", 200, headers=h)


def make_due(uid, n=3):
    with SessionLocal() as db:
        for w in db.query(models.VocabularyWord).limit(n).all():
            db.add(models.UserVocabulary(user_id=uid, word_id=w.id, status="learning", mastery=40.0,
                                         next_review_at=datetime.utcnow() - timedelta(hours=1)))
        db.commit()


def finish_review_round(client, h):
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "review", "size": 4})
    with SessionLocal() as db:
        stored = db.get(models.PracticeSession, s["id"]).questions
    for i, q in enumerate(stored):
        expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
               json={"index": i, "choice_id": q["item_id"], "response_ms": 1500})
    expect(client, "post", f"/api/practice/sessions/{s['id']}/complete", 200, headers=h)


@pytest.fixture
def learner(client):
    return register(client, unique_name("today"))


def test_a_new_learner_gets_one_task_and_no_invented_activity(client, learner):
    _, h = learner
    plan = today(client, h)["today"]
    assert [t["key"] for t in plan["tasks"]] == ["learn"], plan
    assert plan["tasks"][0]["next"]["key"] == "tones" and plan["tasks"][0]["done"] is False
    assert (plan["left"], plan["rounds"], plan["words"], plan["minutes"]) == (1, 0, 0, 0), plan


def test_due_reviews_are_counted_once_and_ticked_off_by_a_real_round(client, learner):
    uid, h = learner
    make_due(uid, 3)
    j = today(client, h)
    assert j["due_reviews"] == 3, j["due_reviews"]
    review = next(t for t in j["today"]["tasks"] if t["key"] == "review")
    assert review["count"] == 3 and review["done"] is False, review  # 3, not 6
    finish_review_round(client, h)
    plan = today(client, h)["today"]
    review = next(t for t in plan["tasks"] if t["key"] == "review")
    assert review["done"] is True and plan["rounds"] == 1 and plan["words"] >= 3, plan


@pytest.fixture(scope="module")
def planned(client):
    """A learner who finished a review round today, with grammar the weakest
    practised skill (22%), listening strong and everything else unpractised."""
    uid, h = register(client, "today_planned")
    make_due(uid, 3)
    finish_review_round(client, h)
    with SessionLocal() as db:
        for us in db.query(models.UserSkill).filter_by(user_id=uid).all():
            us.mastery = {"grammar": 22.0, "listening": 80.0}.get(us.skill.code, 0.0)
        db.commit()
    return uid, h


def test_the_weakest_practised_skill_gets_a_task_and_unpractised_ones_never_do(client, planned):
    _, h = planned
    plan = today(client, h)["today"]
    weak = [t for t in plan["tasks"] if t["key"] == "weak"]
    assert len(weak) == 1 and weak[0]["skill"] == "grammar" and weak[0]["mastery"] == 22, plan["tasks"]
    assert weak[0]["to"].startswith("/practice?source=grammar"), weak[0]
    assert len(plan["tasks"]) <= 4 and all("why" not in t for t in plan["tasks"])
    assert expect(client, "get", "/api/dashboard", 200, headers=h)["dna"]["weak_areas"]


def test_the_assistant_is_given_the_same_real_plan(client, planned):
    uid, _ = planned
    with SessionLocal() as db:
        line = assistant_router._today_line(db, db.get(models.User, uid), "en")
    assert "review the 0 item(s) due [done today]" in line and "grammar (22%)" in line and "today so far: 1" in line, line
