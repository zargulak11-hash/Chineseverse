"""Server-graded practice/review loop, end to end on a fresh database."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/practice.db"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, f"{method.upper()} {url} -> {resp.status_code} (expected {expected}): {resp.text}"
    return resp.json() if resp.content else None


def register(client, name):
    data = expect(client, "post", "/api/auth/register", 201,
                  json={"username": name, "email": f"{name}@example.com", "password": "secret1"})
    return data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}


def skill(uid, code):
    with SessionLocal() as db:
        us = (db.query(models.UserSkill).join(models.Skill)
              .filter(models.UserSkill.user_id == uid, models.Skill.code == code).first())
        return us.mastery if us else 0.0


with TestClient(app) as client:
    uid, h = register(client, "learner")
    _, other = register(client, "otherlearner")
    expect(client, "get", "/api/dashboard", 200, headers=h)  # creates skill rows

    # --- every level/source can build a round from real content
    for lvl in range(1, 10):
        for source in ("vocab", "hanzi", "grammar"):
            s = expect(client, "post", "/api/practice/sessions", 201, headers=h,
                       json={"source": source, "hsk_level": lvl, "size": 4})
            assert s["questions"], (source, lvl)
            for q in s["questions"]:
                assert 3 <= len(q["options"]) <= 4, q
                assert len({o["label"] for o in q["options"]}) == len(q["options"]), q
                assert q["answer"] is None
    print("[PASS] vocab/hanzi/grammar rounds build for HSK 1-9 with distinct options")

    expect(client, "post", "/api/practice/sessions", 401, json={"source": "vocab", "hsk_level": 1})
    expect(client, "post", "/api/practice/sessions", 422, headers=h, json={"source": "vocab"})
    expect(client, "post", "/api/practice/sessions", 422, headers=h, json={"source": "bogus", "hsk_level": 1})

    # --- grading happens on the server
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "vocab", "hsk_level": 1, "size": 6})
    sid, qs = s["id"], s["questions"]
    with SessionLocal() as db:
        stored = db.get(models.PracticeSession, sid).questions
    q0, q1 = qs[0], qs[1]
    wrong = next(o["id"] for o in q0["options"] if o["id"] != stored[0]["item_id"])
    xp_before = expect(client, "get", "/api/me", 200, headers=h)["user"]["total_xp"]

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
    print("[PASS] wrong answer graded server-side, recorded as a mistake, cannot be re-answered")

    vocab_before = skill(uid, "vocabulary")
    r = expect(client, "post", f"/api/practice/sessions/{sid}/answer", 200, headers=h,
               json={"index": 1, "choice_id": stored[1]["item_id"], "response_ms": 2000})
    assert r["correct"] is True and r["mastery"] > 0 and r["xp_gained"] == 2 and r["reaction"]["mood"] == "happy", r
    assert skill(uid, "vocabulary") > vocab_before
    assert skill(uid, "reaction_speed") > 0
    assert expect(client, "get", "/api/me", 200, headers=h)["user"]["total_xp"] == xp_before + 2
    print("[PASS] correct answer raises mastery, Vocabulary + Reaction Speed DNA, and XP")

    for i in range(2, len(qs)):
        expect(client, "post", f"/api/practice/sessions/{sid}/answer", 200, headers=h,
               json={"index": i, "choice_id": stored[i]["item_id"], "response_ms": 9000})
    summary = expect(client, "post", f"/api/practice/sessions/{sid}/complete", 200, headers=h)
    assert summary["correct"] == len(qs) - 1 and summary["total"] == len(qs) and len(summary["missed"]) == 1, summary
    expect(client, "post", f"/api/practice/sessions/{sid}/answer", 409, headers=h, json={"index": 1, "choice_id": stored[1]["item_id"]})
    print(f"[PASS] completed round: {summary['score']}% with mood {summary['reaction']['mood']!r}")

    # --- review brings back what was missed
    review = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "review"})
    with SessionLocal() as db:
        items = [(q["item_type"], q["item_id"]) for q in db.get(models.PracticeSession, review["id"]).questions]
    assert ("vocab", stored[0]["item_id"]) in items, items
    assert expect(client, "get", "/api/practice/review/summary", 200, headers=h)["mistakes"] == 1
    memory_before = skill(uid, "memory")
    with SessionLocal() as db:
        rq = db.get(models.PracticeSession, review["id"]).questions
    idx = next(i for i, q in enumerate(rq) if q["item_id"] == stored[0]["item_id"] and q["item_type"] == "vocab")
    expect(client, "post", f"/api/practice/sessions/{review['id']}/answer", 200, headers=h,
           json={"index": idx, "choice_id": stored[0]["item_id"]})
    assert skill(uid, "memory") > memory_before
    counts = expect(client, "get", "/api/practice/review/summary", 200, headers=h)
    assert counts["mistakes"] == 0, counts  # the one missed word was just recalled correctly
    empty = expect(client, "post", "/api/practice/sessions", 200, headers=other, json={"source": "review"})
    assert empty["id"] is None and empty["empty"] == "nothing_due"
    print("[PASS] review serves missed items, feeds Memory; a fresh learner gets 'nothing due'")

    # --- lessons are practiced through their real content and completed by score
    lessons = expect(client, "get", "/api/lessons?hsk_level=1", 200)
    lesson = None
    for l in lessons:
        items = expect(client, "get", f"/api/lessons/{l['id']}/items", 200)
        if len(items["vocab"]) >= 3:
            lesson = l
            break
    assert lesson is not None, "no HSK1 lesson with linked vocabulary"
    ls = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "lesson", "lesson_id": lesson["id"]})
    with SessionLocal() as db:
        lq = db.get(models.PracticeSession, ls["id"]).questions
    for i, q in enumerate(lq):
        expect(client, "post", f"/api/practice/sessions/{ls['id']}/answer", 200, headers=h, json={"index": i, "choice_id": q["item_id"]})
    done = expect(client, "post", f"/api/practice/sessions/{ls['id']}/complete", 200, headers=h)
    assert done["lesson_status"] == "completed" and done["reaction"]["event"] == "lesson_complete", done
    mine = expect(client, "get", "/api/progress", 200, headers=h)
    assert any(p["lesson_id"] == lesson["id"] and p["status"] == "completed" and p["score"] == 100 for p in mine), mine
    assert expect(client, "get", "/api/progress", 200, headers=other) == []
    print(f"[PASS] lesson {lesson['title']!r} completed through practice (only for this learner)")

    # --- a failed lesson round stays in progress
    ls2 = expect(client, "post", "/api/practice/sessions", 201, headers=other, json={"source": "lesson", "lesson_id": lesson["id"]})
    with SessionLocal() as db:
        lq = db.get(models.PracticeSession, ls2["id"]).questions
    wrong = next(o for o in lq[0]["option_ids"] if o != lq[0]["item_id"])
    expect(client, "post", f"/api/practice/sessions/{ls2['id']}/answer", 200, headers=other, json={"index": 0, "choice_id": wrong})
    fail = expect(client, "post", f"/api/practice/sessions/{ls2['id']}/complete", 200, headers=other)
    assert fail["lesson_status"] == "in_progress" and not fail["passed"], fail
    print("[PASS] a failed lesson round records in_progress, not completed")

print("ALL PRACTICE TESTS PASSED")
