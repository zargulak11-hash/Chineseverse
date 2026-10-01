"""Sequential lesson path (services/lesson_path.py), end to end on a fresh
database: one current lesson, locked lessons refused by every endpoint,
completion only through a passed practice round, existing progress resumed,
and HSK 1 -> HSK 2 progression on the real seeded curriculum."""

import os
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/lesson_path.db"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services import practice as practice_svc  # noqa: E402
from app.services.lesson_path import path_state  # noqa: E402


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, f"{method.upper()} {url} -> {resp.status_code} (expected {expected}): {resp.text}"
    return resp.json() if resp.content else None


def register(client, name):
    data = expect(client, "post", "/api/auth/register", 201,
                  json={"username": name, "email": f"{name}@example.com", "password": "secret1"})
    return data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}


def flat(path):
    return [l for lvl in path["levels"] for l in lvl["lessons"]]


def steps(path):
    return [l for l in flat(path) if l["practicable"]]


def play(client, h, lesson_id, correct=True):
    """Play one real lesson round: every answer right, or every answer wrong."""
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "lesson", "lesson_id": lesson_id})
    with SessionLocal() as db:
        qs = db.get(models.PracticeSession, s["id"]).questions
    for i, q in enumerate(qs):
        choice = q["item_id"] if correct else next(o for o in q["option_ids"] if o != q["item_id"])
        expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h, json={"index": i, "choice_id": choice})
    return expect(client, "post", f"/api/practice/sessions/{s['id']}/complete", 200, headers=h)


with TestClient(app) as client:
    uid, h = register(client, "pathlearner")
    oid, other = register(client, "pathother")

    # --- a new learner: exactly one current lesson, at the start of HSK 1
    path = expect(client, "get", "/api/lessons/path", 200, headers=h)
    expect(client, "get", "/api/lessons/path", 401)
    lessons, stepl = flat(path), steps(path)
    assert [l["status"] for l in lessons].count("current") == 1, path
    first = stepl[0]
    assert first["status"] == "current" and path["current_lesson_id"] == first["id"], first
    assert path["current_level"] == 1 and path["levels"][0]["level"] == 1 and path["levels"][0]["status"] == "current"
    assert all(l["status"] == "locked" for l in stepl[1:]), "every later step starts locked"
    cur_pos = lessons.index(first)
    assert all(l["status"] == "available" for l in lessons[:cur_pos]), "reading-only lessons before it are open"
    assert all(lv["status"] == "locked" for lv in path["levels"][1:]), "HSK 2+ start locked"
    assert [lv["level"] for lv in path["levels"]] == sorted(lv["level"] for lv in path["levels"])
    assert {7, 8, 9} <= {lv["level"] for lv in path["levels"]}, "the advanced band is walked as stages 7, 8, 9"
    print(f"[PASS] new learner: one current lesson ({first['title']!r}), {len(stepl) - 1} later steps locked")

    # --- every step of the path can really be played (nobody gets stuck)
    with SessionLocal() as db:
        u = db.get(models.User, uid)
        for e in path_state(db, u).entries:
            if e.practicable:
                assert practice_svc.build_session(db, u, "lesson", lesson_id=e.lesson.id) is not None, e.lesson.title
    print(f"[PASS] all {len(stepl)} path steps build a real practice round")

    # --- locked lessons are refused by the backend, not just hidden
    locked = stepl[1]
    for url in (f"/api/lessons/{locked['id']}", f"/api/lessons/{locked['id']}/items"):
        body = expect(client, "get", url, 403, headers=h)
        assert body["code"] == "lesson_locked" and body["current_lesson_id"] == first["id"], body
        expect(client, "get", url, 401)  # no token -> no bypass either
    body = expect(client, "post", "/api/practice/sessions", 403, headers=h, json={"source": "lesson", "lesson_id": locked["id"]})
    assert body["code"] == "lesson_locked", body
    last = stepl[-1]
    expect(client, "get", f"/api/lessons/{last['id']}", 403, headers=h)
    expect(client, "get", f"/api/lessons/{first['id']}", 200, headers=h)
    expect(client, "get", "/api/lessons/999999", 404, headers=h)
    print("[PASS] locked lesson: GET, /items and a practice round are all 403 lesson_locked")

    # --- the catalogue stays public but never carries lesson bodies
    assert all(l["content"] is None for l in expect(client, "get", "/api/lessons", 200)), "anonymous list leaks content"
    assert all(l["content"] is None for l in expect(client, "get", "/api/lessons", 200, headers=h)), "learner list leaks content"
    print("[PASS] /api/lessons lists titles only; content comes from the gated GET /{id}")

    # --- the client cannot complete a lesson for itself
    expect(client, "post", "/api/progress", 403, headers=h, json={"lesson_id": first["id"], "status": "completed", "score": 100})
    expect(client, "post", "/api/progress", 403, headers=h, json={"lesson_id": locked["id"], "status": "completed", "score": 100})
    row = expect(client, "post", "/api/progress", 201, headers=h, json={"lesson_id": first["id"], "status": "in_progress"})
    expect(client, "patch", f"/api/progress/{row['id']}", 403, headers=h, json={"status": "completed", "score": 100})
    expect(client, "put", f"/api/progress/{row['id']}", 403, headers=h, json={"status": "completed", "score": 100})
    again = expect(client, "get", "/api/lessons/path", 200, headers=h)
    assert again["current_lesson_id"] == first["id"] and steps(again)[1]["status"] == "locked", again["current_lesson_id"]
    print("[PASS] POST/PATCH/PUT status=completed on /api/progress is 403; the path did not move")

    # --- an unfinished (failed) lesson does not unlock the next one
    fail = play(client, h, first["id"], correct=False)
    assert not fail["passed"] and fail["lesson_status"] == "in_progress" and fail["next_lesson_id"] is None, fail
    after_fail = expect(client, "get", "/api/lessons/path", 200, headers=h)
    assert after_fail["current_lesson_id"] == first["id"] and steps(after_fail)[1]["status"] == "locked"
    expect(client, "get", f"/api/lessons/{locked['id']}", 403, headers=h)
    print("[PASS] a failed round keeps the lesson current and the next one locked")

    # --- passing the current lesson unlocks exactly the next step
    win = play(client, h, first["id"])
    assert win["passed"] and win["lesson_status"] == "completed", win
    assert win["next_lesson_id"] == stepl[1]["id"], win
    p2 = expect(client, "get", "/api/lessons/path", 200, headers=h)
    s2 = steps(p2)
    assert s2[0]["status"] == "completed" and s2[1]["status"] == "current" and s2[2]["status"] == "locked", [x["status"] for x in s2[:3]]
    assert p2["current_lesson_id"] == stepl[1]["id"] and p2["completed"] == 1
    assert [l["status"] for l in flat(p2)].count("current") == 1
    expect(client, "get", f"/api/lessons/{stepl[1]['id']}", 200, headers=h)
    expect(client, "get", f"/api/lessons/{stepl[2]['id']}", 403, headers=h)
    print("[PASS] passing the current lesson completes it and unlocks exactly the next step")

    # --- completed lessons stay open for review, and reviewing them unlocks nothing
    done = expect(client, "get", f"/api/lessons/{first['id']}", 200, headers=h)
    assert done["path_status"] == "completed", done
    expect(client, "get", f"/api/lessons/{first['id']}/items", 200, headers=h)
    review_pass = play(client, h, first["id"])
    review_fail = play(client, h, first["id"], correct=False)
    assert review_pass["lesson_status"] == review_fail["lesson_status"] == "completed"
    assert review_pass["next_lesson_id"] is None and review_pass["reaction"]["event"] != "lesson_complete"
    p3 = expect(client, "get", "/api/lessons/path", 200, headers=h)
    assert p3["current_lesson_id"] == stepl[1]["id"] and steps(p3)[2]["status"] == "locked"
    print("[PASS] a completed lesson stays readable/practicable; re-practicing it never advances the path")

    # --- one learner's progress never moves another's path
    po = expect(client, "get", "/api/lessons/path", 200, headers=other)
    assert po["current_lesson_id"] == first["id"] and po["completed"] == 0, po["current_lesson_id"]
    expect(client, "get", f"/api/lessons/{stepl[1]['id']}", 403, headers=other)
    print("[PASS] the other learner is still at lesson 1 with lesson 2 locked")

    # --- a round left open on a lesson that is locked cannot complete it
    with SessionLocal() as db:
        u = db.get(models.User, oid)
        stale = practice_svc.build_session(db, u, "lesson", lesson_id=stepl[3]["id"])  # bypasses the router gate
        stale_id, sq = stale.id, stale.questions
    for i, q in enumerate(sq):
        expect(client, "post", f"/api/practice/sessions/{stale_id}/answer", 200, headers=other, json={"index": i, "choice_id": q["item_id"]})
    res = expect(client, "post", f"/api/practice/sessions/{stale_id}/complete", 200, headers=other)
    assert res["passed"] and res["lesson_status"] is None and res["next_lesson_id"] is None, res
    po2 = expect(client, "get", "/api/lessons/path", 200, headers=other)
    assert po2["current_lesson_id"] == first["id"] and steps(po2)[3]["status"] == "locked"
    print("[PASS] a perfect round on a locked lesson grades the words but completes nothing")

    # --- existing progress is kept: completed 1-10 resumes at 11
    lid, lh = register(client, "pathlegacy")
    gid, gh = register(client, "pathgappy")
    with SessionLocal() as db:
        for s in stepl[:10]:
            db.add(models.Progress(user_id=lid, lesson_id=s["id"], status="completed", score=90, completed_at=datetime.utcnow()))
        db.add(models.Progress(user_id=gid, lesson_id=stepl[5]["id"], status="completed", score=80, completed_at=datetime.utcnow()))
        db.commit()
    pl = expect(client, "get", "/api/lessons/path", 200, headers=lh)
    assert pl["current_lesson_id"] == stepl[10]["id"] and pl["completed"] == 10, pl["current_lesson_id"]
    assert all(s["status"] == "completed" for s in steps(pl)[:10]) and steps(pl)[11]["status"] == "locked"
    pg = expect(client, "get", "/api/lessons/path", 200, headers=gh)
    sg = steps(pg)
    assert pg["current_lesson_id"] == stepl[6]["id"], pg["current_lesson_id"]
    assert [s["status"] for s in sg[:7]] == ["available"] * 5 + ["completed", "current"] and sg[7]["status"] == "locked"
    expect(client, "get", f"/api/lessons/{stepl[2]['id']}", 200, headers=gh)
    gap = play(client, gh, stepl[2]["id"])  # filling an old gap
    assert gap["lesson_status"] == "completed" and gap["next_lesson_id"] == stepl[6]["id"], gap
    assert expect(client, "get", "/api/lessons/path", 200, headers=gh)["current_lesson_id"] == stepl[6]["id"]
    print("[PASS] pre-path progress resumes after the furthest completed lesson; earlier gaps stay open, nothing reset")

    # --- HSK progression on the real curriculum: finish HSK 1 -> HSK 2 opens
    hsk1 = [s for s in steps(expect(client, "get", "/api/lessons/path", 200, headers=h)) if s["status"] != "completed"]
    level_of = {l["id"]: lv["level"] for lv in path["levels"] for l in lv["lessons"]}
    hsk1 = [s for s in hsk1 if level_of[s["id"]] == 1]
    for s in hsk1:
        cur = expect(client, "get", "/api/lessons/path", 200, headers=h)["current_lesson_id"]
        assert cur == s["id"], (cur, s["id"])
        assert play(client, h, s["id"])["lesson_status"] == "completed"
    ph = expect(client, "get", "/api/lessons/path", 200, headers=h)
    by_level = {lv["level"]: lv for lv in ph["levels"]}
    assert by_level[1]["status"] == "completed" and by_level[1]["completed"] == by_level[1]["total"], by_level[1]
    assert by_level[2]["status"] == "current" and ph["current_level"] == 2, by_level[2]["status"]
    assert by_level[3]["status"] == "locked"
    first_hsk2 = next(s for s in steps(ph) if level_of[s["id"]] == 2)
    assert ph["current_lesson_id"] == first_hsk2["id"]
    print(f"[PASS] completing all {by_level[1]['total']} HSK 1 steps opens HSK 2 at its first lesson; HSK 3 stays locked")

    # --- admins can read any lesson (they author them) but still progress in order
    aid, ah = register(client, "pathadmin")
    with SessionLocal() as db:
        db.get(models.User, aid).is_admin = True
        db.commit()
    expect(client, "get", f"/api/lessons/{last['id']}", 200, headers=ah)
    assert any(l["content"] for l in expect(client, "get", "/api/lessons", 200, headers=ah))
    expect(client, "post", "/api/practice/sessions", 403, headers=ah, json={"source": "lesson", "lesson_id": last["id"]})
    print("[PASS] admin reads any lesson's content but cannot practice past the path")

print("ALL LESSON PATH TESTS PASSED")
