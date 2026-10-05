"""Server-graded practice/review loop: the server builds the questions,
grades each answer, and alone decides mastery, XP, mistakes, Learning DNA
and lesson completion."""

import pytest

from app import models
from app.database import SessionLocal
from helpers import expect, register, unique_name


def skill(uid, code):
    with SessionLocal() as db:
        us = (db.query(models.UserSkill).join(models.Skill)
              .filter(models.UserSkill.user_id == uid, models.Skill.code == code).first())
        return us.mastery if us else 0.0


def stored_questions(sid):
    with SessionLocal() as db:
        return db.get(models.PracticeSession, sid).questions


@pytest.fixture
def learner(client):
    uid, h = register(client, unique_name())
    expect(client, "get", "/api/dashboard", 200, headers=h)  # creates skill rows
    return uid, h


@pytest.mark.parametrize("source", ["vocab", "hanzi", "grammar"])
def test_every_level_builds_a_round_from_real_content(client, learner, source):
    _, h = learner
    for lvl in range(1, 10):
        s = expect(client, "post", "/api/practice/sessions", 201, headers=h,
                   json={"source": source, "hsk_level": lvl, "size": 4})
        assert s["questions"], (source, lvl)
        for q in s["questions"]:
            assert 3 <= len(q["options"]) <= 4, q
            assert len({o["label"] for o in q["options"]}) == len(q["options"]), q
            # The answer never leaves the server before grading.
            assert q["answer"] is None


def test_session_request_validation(client, learner):
    _, h = learner
    expect(client, "post", "/api/practice/sessions", 401, json={"source": "vocab", "hsk_level": 1})
    expect(client, "post", "/api/practice/sessions", 422, headers=h, json={"source": "vocab"})
    expect(client, "post", "/api/practice/sessions", 422, headers=h, json={"source": "bogus", "hsk_level": 1})


def test_graded_round_then_review_brings_back_the_miss(client, learner):
    uid, h = learner
    _, other = register(client, "practice_other")
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "vocab", "hsk_level": 1, "size": 6})
    sid, qs = s["id"], s["questions"]
    stored = stored_questions(sid)
    q0 = qs[0]
    wrong = next(o["id"] for o in q0["options"] if o["id"] != stored[0]["item_id"])
    xp_before = expect(client, "get", "/api/me", 200, headers=h)["user"]["total_xp"]

    # Wrong answer: graded server-side, recorded as a mistake, can't be re-answered;
    # another learner can't answer someone else's round.
    expect(client, "post", f"/api/practice/sessions/{sid}/answer", 422, headers=h, json={"index": 0, "choice_id": -5})
    expect(client, "post", f"/api/practice/sessions/{sid}/answer", 404, headers=other, json={"index": 0, "choice_id": wrong})
    r = expect(client, "post", f"/api/practice/sessions/{sid}/answer", 200, headers=h,
               json={"index": 0, "choice_id": wrong, "response_ms": 2500})
    assert r["correct"] is False and r["correct_id"] == stored[0]["item_id"] and r["reaction"]["mood"] == "encouraging", r
    expect(client, "post", f"/api/practice/sessions/{sid}/answer", 409, headers=h, json={"index": 0, "choice_id": wrong})
    with SessionLocal() as db:
        word = db.get(models.VocabularyWord, stored[0]["item_id"])
        m = db.query(models.LearningMistake).filter_by(user_id=uid, mistake_type="word", reference=word.simplified).first()
        assert m is not None and not m.mastered

    # Correct answer raises mastery, Vocabulary + Reaction Speed DNA, and XP.
    vocab_before = skill(uid, "vocabulary")
    r = expect(client, "post", f"/api/practice/sessions/{sid}/answer", 200, headers=h,
               json={"index": 1, "choice_id": stored[1]["item_id"], "response_ms": 2000})
    assert r["correct"] is True and r["mastery"] > 0 and r["xp_gained"] == 2 and r["reaction"]["mood"] == "happy", r
    assert skill(uid, "vocabulary") > vocab_before
    assert skill(uid, "reaction_speed") > 0
    assert expect(client, "get", "/api/me", 200, headers=h)["user"]["total_xp"] == xp_before + 2

    for i in range(2, len(qs)):
        expect(client, "post", f"/api/practice/sessions/{sid}/answer", 200, headers=h,
               json={"index": i, "choice_id": stored[i]["item_id"], "response_ms": 9000})
    summary = expect(client, "post", f"/api/practice/sessions/{sid}/complete", 200, headers=h)
    assert summary["correct"] == len(qs) - 1 and summary["total"] == len(qs) and len(summary["missed"]) == 1, summary
    expect(client, "post", f"/api/practice/sessions/{sid}/answer", 409, headers=h, json={"index": 1, "choice_id": stored[1]["item_id"]})

    # Review serves the missed item and feeds Memory.
    review = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "review"})
    rq = stored_questions(review["id"])
    assert ("vocab", stored[0]["item_id"]) in [(q["item_type"], q["item_id"]) for q in rq]
    assert expect(client, "get", "/api/practice/review/summary", 200, headers=h)["mistakes"] == 1
    memory_before = skill(uid, "memory")
    idx = next(i for i, q in enumerate(rq) if q["item_id"] == stored[0]["item_id"] and q["item_type"] == "vocab")
    expect(client, "post", f"/api/practice/sessions/{review['id']}/answer", 200, headers=h,
           json={"index": idx, "choice_id": stored[0]["item_id"]})
    assert skill(uid, "memory") > memory_before
    counts = expect(client, "get", "/api/practice/review/summary", 200, headers=h)
    assert counts["mistakes"] == 0, counts  # the one missed word was just recalled correctly

    # A learner with nothing missed gets "nothing due", not an empty round.
    empty = expect(client, "post", "/api/practice/sessions", 200, headers=other, json={"source": "review"})
    assert empty["id"] is None and empty["empty"] == "nothing_due"


def current_lesson(client, h):
    path = expect(client, "get", "/api/lessons/path", 200, headers=h)
    return next(l for lvl in path["levels"] for l in lvl["lessons"] if l["id"] == path["current_lesson_id"])


def test_lesson_is_completed_only_by_a_passing_round(client, learner):
    _, h = learner
    _, other = register(client, "lesson_bystander")
    lesson = current_lesson(client, h)
    items = expect(client, "get", f"/api/lessons/{lesson['id']}/items", 200, headers=h)
    assert items["vocab"] or items["grammar"], "current lesson has nothing to practice"
    ls = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "lesson", "lesson_id": lesson["id"]})
    for i, q in enumerate(stored_questions(ls["id"])):
        expect(client, "post", f"/api/practice/sessions/{ls['id']}/answer", 200, headers=h, json={"index": i, "choice_id": q["item_id"]})
    done = expect(client, "post", f"/api/practice/sessions/{ls['id']}/complete", 200, headers=h)
    assert done["lesson_status"] == "completed" and done["reaction"]["event"] == "lesson_complete", done
    mine = expect(client, "get", "/api/progress", 200, headers=h)
    assert any(p["lesson_id"] == lesson["id"] and p["status"] == "completed" and p["score"] == 100 for p in mine), mine
    assert expect(client, "get", "/api/progress", 200, headers=other) == []


def test_failed_lesson_round_stays_in_progress(client, learner):
    _, h = learner
    lesson = current_lesson(client, h)
    ls = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "lesson", "lesson_id": lesson["id"]})
    lq = stored_questions(ls["id"])
    wrong = next(o for o in lq[0]["option_ids"] if o != lq[0]["item_id"])
    expect(client, "post", f"/api/practice/sessions/{ls['id']}/answer", 200, headers=h, json={"index": 0, "choice_id": wrong})
    fail = expect(client, "post", f"/api/practice/sessions/{ls['id']}/complete", 200, headers=h)
    assert fail["lesson_status"] == "in_progress" and not fail["passed"], fail
