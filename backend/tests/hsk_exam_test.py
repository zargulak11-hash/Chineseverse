"""HSK level final exams (services/hsk_exam.py) end to end on a fresh
database: the exam gates the next level, the server alone grades it, and an
attempt is a one-shot protected session (leaving, hiding, reopening or
running out of time ends it with 0)."""

import os
import re
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/hsk_exam.db"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services import hsk_exam  # noqa: E402
from app.services.lesson_path import ordered_lessons, path_state  # noqa: E402


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, f"{method.upper()} {url} -> {resp.status_code} (expected {expected}): {resp.text[:300]}"
    return resp.json() if resp.content else None


def register(client, name):
    data = expect(client, "post", "/api/auth/register", 201,
                  json={"username": name, "email": f"{name}@example.com", "password": "secret1"})
    return data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}


def complete_levels(uid, levels):
    """Completed lesson rows for every step of these levels (as passing their rounds would)."""
    with SessionLocal() as db:
        u = db.get(models.User, uid)
        for e in path_state(db, u).entries:
            if e.level in levels and e.practicable:
                db.add(models.Progress(user_id=uid, lesson_id=e.lesson.id, status="completed", score=90,
                                       completed_at=datetime.utcnow()))
        db.commit()


def stored(attempt_id):
    with SessionLocal() as db:
        return db.get(models.HSKExamAttempt, attempt_id).questions


def answer_all(client, h, attempt, right=True):
    qs = stored(attempt["id"])
    for i, q in enumerate(qs):
        choice = q["item_id"] if right else next(o for o in q["option_ids"] if o != q["item_id"])
        expect(client, "post", f"/api/exams/attempts/{attempt['id']}/answer", 200, headers=h,
               json={"index": i, "choice_id": choice, "correct": True, "score": 100})


def path(client, h):
    return expect(client, "get", "/api/lessons/path", 200, headers=h)


def first_lesson_of(p, level):
    return next(l for lv in p["levels"] if lv["level"] == level for l in lv["lessons"] if l["practicable"])


with TestClient(app) as client:
    uid, h = register(client, "examlearner")
    oid, other = register(client, "examother")

    # 1-2, 5, 19: a new learner starts at lesson 1; no exam is open
    p = path(client, h)
    assert p["exam_level"] is None and p["current_level"] == 1
    ov = expect(client, "get", "/api/exams", 200, headers=h)
    assert ov["exam_level"] is None and all(l["exam"] == "locked" for l in ov["levels"])
    assert ov["pass_score"] == 80.0 and ov["question_count"] == 20
    body = expect(client, "post", "/api/exams/1/start", 403, headers=h)
    assert body["code"] == "exam_locked"
    expect(client, "post", "/api/exams/2/start", 403, headers=h)
    expect(client, "get", "/api/exams", 401)
    print("[PASS] new learner: no exam open, starting one (any level) is refused")

    # 3-4: finishing HSK 1 opens its exam -- not HSK 2
    complete_levels(uid, {1})
    p = path(client, h)
    assert p["exam_level"] == 1 and p["current_lesson_id"] is None and p["current_level"] == 1, p["exam_level"]
    lv = {x["level"]: x for x in p["levels"]}
    assert lv[1]["exam"] == "ready" and lv[1]["status"] == "current" and lv[2]["status"] == "locked"
    hsk2 = first_lesson_of(p, 2)
    assert hsk2["status"] == "locked"
    expect(client, "get", f"/api/lessons/{hsk2['id']}", 403, headers=h)
    expect(client, "post", "/api/practice/sessions", 403, headers=h, json={"source": "lesson", "lesson_id": hsk2["id"]})
    assert expect(client, "get", "/api/dashboard", 200, headers=h)["hsk_level"] == 1
    print("[PASS] all HSK 1 lessons done -> HSK 1 exam ready; HSK 2 stays locked (lesson, practice, dashboard)")

    # 6, 22, 23: one attempt, real HSK 1 material, no answers in the payload
    a1 = expect(client, "post", "/api/exams/1/start", 201, headers=h)
    assert a1["status"] == "in_progress" and a1["total"] == len(a1["questions"]) == 20 and a1["seconds_left"] > 1100
    flat = repr(a1["questions"])
    assert "item_id" not in flat and "correct" not in flat and "'answer'" not in flat
    with SessionLocal() as db:
        taught = {(t, r.id) for t, r in hsk_exam.level_material(db, 1)}
        level1 = db.query(models.HSKLevel).filter_by(level=1).one().id
        for q in stored(a1["id"]):
            assert (q["item_type"], q["item_id"]) in taught, q
            model = models.VocabularyWord if q["item_type"] == "vocab" else models.GrammarTopic
            assert db.get(model, q["item_id"]).hsk_level_id == level1
    print("[PASS] exam built from what HSK 1 lessons taught; the browser gets no answer, id or correctness")

    # 7: a second simultaneous attempt is refused (API and database)
    body = expect(client, "post", "/api/exams/1/start", 409, headers=h)
    assert body["code"] == "exam_in_progress" and body["attempt_id"] == a1["id"]
    with SessionLocal() as db:
        db.add(models.HSKExamAttempt(user_id=uid, level=1, status="in_progress", questions=[], answers=[],
                                     total=0, violations=[], started_at=datetime.utcnow(),
                                     expires_at=datetime.utcnow() + timedelta(minutes=5)))
        try:
            db.commit()
            raise AssertionError("a second active attempt was stored")
        except IntegrityError:
            db.rollback()
    print("[PASS] one active attempt per user: a second start is 409, and the database refuses a second row")

    # 18: another user cannot see or touch it
    for method, url, kw in (("get", f"/api/exams/attempts/{a1['id']}", {}),
                            ("post", f"/api/exams/attempts/{a1['id']}/answer", {"json": {"index": 0, "choice_id": 1}}),
                            ("post", f"/api/exams/attempts/{a1['id']}/submit", {}),
                            ("post", f"/api/exams/attempts/{a1['id']}/violation", {"json": {"reason": "hidden"}})):
        expect(client, method, url, 404, headers=other, **kw)
    print("[PASS] another learner gets 404 on every attempt route")

    # 8-11, 13, 21: wrong answers fail; the client cannot send a score or a pass
    expect(client, "post", f"/api/exams/attempts/{a1['id']}/answer", 422, headers=h, json={"index": 0, "choice_id": -5})
    expect(client, "post", f"/api/exams/attempts/{a1['id']}/answer", 422, headers=h, json={"index": 99, "choice_id": 1})
    answer_all(client, h, a1, right=False)
    r = expect(client, "post", f"/api/exams/attempts/{a1['id']}/submit", 200, headers=h,
               json={"score": 100, "passed": True, "status": "passed"})
    assert r["status"] == "failed" and r["score"] == 0.0 and r["correct"] == 0 and r["incorrect"] == 20 and not r["passed"]
    p = path(client, h)
    assert p["exam_level"] == 1 and first_lesson_of(p, 2)["status"] == "locked"
    assert all(l["status"] == "completed" for l in p["levels"][0]["lessons"] if l["practicable"])
    expect(client, "post", f"/api/exams/attempts/{a1['id']}/submit", 409, headers=h)  # over: no second grading
    expect(client, "post", f"/api/exams/attempts/{a1['id']}/answer", 409, headers=h, json={"index": 0, "choice_id": 1})
    print("[PASS] all wrong -> failed 0/20 (client score/passed ignored); HSK 2 locked; every HSK 1 lesson still completed")

    # partly right: the score is the server's count
    a2 = expect(client, "post", "/api/exams/1/start", 201, headers=h)
    qs = stored(a2["id"])
    for i, q in enumerate(qs):
        choice = q["item_id"] if i < 15 else next(o for o in q["option_ids"] if o != q["item_id"])
        expect(client, "post", f"/api/exams/attempts/{a2['id']}/answer", 200, headers=h, json={"index": i, "choice_id": choice})
    r = expect(client, "post", f"/api/exams/attempts/{a2['id']}/submit", 200, headers=h)
    assert r["correct"] == 15 and r["score"] == 75.0 and r["status"] == "failed", r
    print("[PASS] 15/20 -> 75.0, below the server's 80% pass mark -> failed")

    # 14-15: leaving / hiding the exam invalidates it with 0
    a3 = expect(client, "post", "/api/exams/1/start", 201, headers=h)
    answer_all(client, h, a3, right=True)
    r = expect(client, "post", f"/api/exams/attempts/{a3['id']}/violation", 200, headers=h, json={"reason": "hidden"})
    assert r["status"] == "invalidated" and r["score"] == 0.0 and r["violations"] == ["hidden"] and not r["passed"]
    expect(client, "post", f"/api/exams/attempts/{a3['id']}/submit", 409, headers=h)
    assert path(client, h)["exam_level"] == 1
    print("[PASS] hiding the exam (even with every answer right) -> invalidated, score 0, cannot be submitted after")

    # 17, 20: reopening an in-progress attempt (reload / second tab / URL) ends it
    a4 = expect(client, "post", "/api/exams/1/start", 201, headers=h)
    r = expect(client, "get", f"/api/exams/attempts/{a4['id']}", 200, headers=h)
    assert r["status"] == "invalidated" and r["violations"] == ["reopened"] and r["score"] == 0.0
    assert expect(client, "get", f"/api/exams/attempts/{a4['id']}", 200, headers=h)["status"] == "invalidated"
    expect(client, "post", f"/api/exams/attempts/{a4['id']}/answer", 409, headers=h, json={"index": 0, "choice_id": 1})
    print("[PASS] reopening an attempt (reload, new tab, URL) invalidates it; it cannot be continued")

    # 16: an attempt nobody submits expires with 0
    a5 = expect(client, "post", "/api/exams/1/start", 201, headers=h)
    with SessionLocal() as db:
        db.get(models.HSKExamAttempt, a5["id"]).expires_at = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
    body = expect(client, "post", f"/api/exams/attempts/{a5['id']}/answer", 409, headers=h, json={"index": 0, "choice_id": 1})
    assert body["code"] == "exam_over" and body["result"]["status"] == "expired" and body["result"]["score"] == 0.0
    a6 = expect(client, "post", "/api/exams/1/start", 201, headers=h)
    with SessionLocal() as db:
        db.get(models.HSKExamAttempt, a6["id"]).expires_at = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
    ov = expect(client, "get", "/api/exams", 200, headers=h)  # a vanished browser: the next request expires it
    assert ov["active_attempt_id"] is None
    with SessionLocal() as db:
        assert db.get(models.HSKExamAttempt, a6["id"]).status == "expired"
    print("[PASS] unsubmitted attempts expire with 0 (on the next request -- also when the browser vanished)")

    # 12: passing opens HSK 2 at its first lesson
    a7 = expect(client, "post", "/api/exams/1/start", 201, headers=h)
    answer_all(client, h, a7, right=True)
    r = expect(client, "post", f"/api/exams/attempts/{a7['id']}/submit", 200, headers=h)
    assert r["status"] == "passed" and r["score"] == 100.0 and r["passed"]
    p = path(client, h)
    assert p["exam_level"] is None and p["current_lesson_id"] == first_lesson_of(p, 2)["id"] and p["current_level"] == 2
    assert {x["level"]: x["exam"] for x in p["levels"]}[1] == "passed"
    expect(client, "get", f"/api/lessons/{first_lesson_of(p, 2)['id']}", 200, headers=h)
    assert expect(client, "get", "/api/dashboard", 200, headers=h)["hsk_level"] == 2
    assert expect(client, "get", "/api/hsk/roadmap", 200, headers=h)["current_level"] == 2
    ov = expect(client, "get", "/api/exams", 200, headers=h)
    l1 = next(x for x in ov["levels"] if x["level"] == 1)
    assert l1["exam"] == "passed" and l1["attempts"] == 7 and l1["best_score"] == 100.0
    expect(client, "post", "/api/exams/1/start", 403, headers=h)  # nothing to retake
    print("[PASS] 20/20 -> passed; HSK 2 opens at its first lesson; dashboard and Roadmap say HSK 2")

    # progress from before exams existed is never re-locked
    gid, gh = register(client, "examlegacy")
    complete_levels(gid, {1})
    with SessionLocal() as db:
        u = db.get(models.User, gid)
        st = path_state(db, u)
        l2 = next(e for e in st.entries if e.level == 2 and e.practicable)
        db.add(models.Progress(user_id=gid, lesson_id=l2.lesson.id, status="completed", score=80, completed_at=datetime.utcnow()))
        db.commit()
    p = path(client, gh)
    assert p["exam_level"] is None and p["current_level"] == 2
    assert {x["level"]: x["exam"] for x in p["levels"]}[1] == "cleared"
    print("[PASS] a learner already past HSK 1 (progress from before exams) is not sent back to an exam")

    # the last step: HSK 9's final exam
    fid, fh = register(client, "examfinal")
    complete_levels(fid, set(range(1, 10)))
    p = path(client, fh)
    assert p["exam_level"] == 9 and p["current_lesson_id"] is None
    a9 = expect(client, "post", "/api/exams/9/start", 201, headers=fh)
    with SessionLocal() as db:
        taught9 = {(t, r.id) for t, r in hsk_exam.level_material(db, 9)}
    assert all((q["item_type"], q["item_id"]) in taught9 for q in stored(a9["id"]))
    answer_all(client, fh, a9, right=True)
    assert expect(client, "post", f"/api/exams/attempts/{a9['id']}/submit", 200, headers=fh)["status"] == "passed"
    p = path(client, fh)
    assert p["exam_level"] is None and {x["level"]: x["exam"] for x in p["levels"]}[9] == "passed"
    print("[PASS] all of HSK 1-9 done -> the HSK 9 final exam (its own stage's material); passing it completes the path")

    # every level 1-9 can build a full exam from its lessons
    with SessionLocal() as db:
        for level in range(1, 10):
            assert len(hsk_exam.level_material(db, level)) >= 20, level
    print("[PASS] every HSK level 1-9 has at least 20 taught items to examine")

    # ru: options in one language
    rid, rh = register(client, "examru")
    complete_levels(rid, {1})
    ar = expect(client, "post", "/api/exams/1/start", 201, headers={**rh, "X-Locale": "ru"})
    cyr = re.compile(r"[А-Яа-яЁё]")
    for q in ar["questions"]:
        if q["type"] in ("word_to_meaning", "listen_to_word"):
            marks = [bool(cyr.search(o["label"] or "")) for o in q["options"]]
            assert all(marks) or not any(marks), q
    print("[PASS] ru exam: meaning options are all Russian (never one translated option among English ones)")

print("ALL HSK EXAM TESTS PASSED")
