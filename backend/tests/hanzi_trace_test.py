"""Hanzi stroke tracing is checked on the server (services/stroke_match.py,
routers/hanzi.py): forged results, replays, foreign attempts and drawings
that aren't the character never move writing mastery; a real trace does."""

import os
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/trace.db"
os.environ["SMTP_HOST"] = "smtp.invalid"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from trace_helpers import hand_stroke, hand_trace, start, stroke_data, trace  # noqa: E402


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, f"{method.upper()} {url} -> {resp.status_code} (expected {expected}): {resp.text[:300]}"
    return resp.json() if resp.content else None


def register(client, name):
    data = expect(client, "post", "/api/auth/register", 201,
                  json={"username": name, "email": f"{name}@example.com", "password": "secret1"})
    return data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}


def state(uid, hid):
    with SessionLocal() as db:
        rec = db.query(models.UserHanzi).filter_by(user_id=uid, hanzi_id=hid).first()
        u = db.get(models.User, uid)
        writing = next((s.mastery for s in u.user_skills if s.skill and s.skill.code == "writing"), 0.0)
        return ((rec.writing_mastery or 0.0) if rec else 0.0, (rec.times_written or 0) if rec else 0, writing, u.total_xp)


def write(client, h, hid, aid, strokes):
    return client.post(f"/api/hanzi/{hid}/write", headers=h, json={"attempt_id": aid, "strokes": strokes})


with TestClient(app) as client:
    uid, h = register(client, "tracer")
    oid, oh = register(client, "othertracer")
    with SessionLocal() as db:
        hz = db.query(models.Hanzi).filter(models.Hanzi.character == "好").first()
        other = db.query(models.Hanzi).filter(models.Hanzi.character == "人").first()
        hid, other_id = hz.id, other.id
        n = len(hz.stroke_data["medians"])
    sd, other_sd = stroke_data(hid), stroke_data(other_id)
    expect(client, "get", "/api/dashboard", 200, headers=h)
    base = state(uid, hid)

    # ---------------------------------------------- forged results
    forged = [
        {"total_mistakes": 0},
        {"total_mistakes": 0, "correct": True, "completed": True, "mastery": 100, "writing_mastery": 100, "score": 100, "xp": 999},
        {"correct": True},
        {"completed": True, "strokes_completed": n},
    ]
    for _ in range(5):
        for body in forged:
            r = client.post(f"/api/hanzi/{hid}/write", headers=h, json=body)
            assert r.status_code == 422, (body, r.status_code)
    assert state(uid, hid) == base, (state(uid, hid), base)
    print("[PASS] total_mistakes / correct / completed / mastery / score / xp from the browser change nothing (422)")

    # ---------------------------------------------- invalid drawings, each on a fresh attempt
    scribble = [[100.0, 100.0], [120.0, 140.0], [160.0, 120.0]]
    cases = {
        "scribbles claimed as correct": [{"points": scribble, "matched": True}] * n,
        "only half the strokes": hand_trace(sd)[: n // 2],
        "strokes out of order": [hand_trace(sd)[1], hand_trace(sd)[0]] + hand_trace(sd)[2:],
        "another character's strokes": hand_trace(other_sd)[:n] if len(other_sd["medians"]) >= n else hand_trace(other_sd),
        "strokes after the character was complete": hand_trace(sd) + [{"points": scribble, "matched": False}],
        "points far outside the box": [{"points": [[99999.0, 5.0], [100000.0, 6.0]], "matched": True}] + hand_trace(sd)[1:],
        "only misses": [{"points": scribble, "matched": False}] * 3,
        "exact median vertices of another stroke": [{"points": [list(p) for p in sd["medians"][-1]], "matched": True}] + hand_trace(sd)[1:],
    }
    for label, strokes in cases.items():
        aid = start(client, h, hid)
        r = write(client, h, hid, aid, strokes)
        assert r.status_code == 422, (label, r.status_code, r.text)
        assert r.json()["detail"].startswith("Trace not accepted"), r.json()
        # the attempt is spent: the forger can't retry on it
        assert write(client, h, hid, aid, hand_trace(sd)).status_code == 409, label
    for bad in ([], [{"points": [[1.0, 2.0]], "matched": True}]):
        aid = start(client, h, hid)
        assert write(client, h, hid, aid, bad).status_code == 422
    assert state(uid, hid) == base, (state(uid, hid), base)
    print(f"[PASS] {len(cases) + 2} kinds of invalid / wrong / incomplete drawings are rejected and spend the attempt")

    # ---------------------------------------------- too fast, expired, superseded
    r = client.post(f"/api/hanzi/{hid}/write/start", headers=h)
    aid = r.json()["attempt_id"]
    r = write(client, h, hid, aid, hand_trace(sd))
    assert r.status_code == 422 and "faster" in r.json()["detail"], r.text
    aid = start(client, h, hid, seconds_ago=31 * 60)
    assert write(client, h, hid, aid, hand_trace(sd)).status_code == 409
    old = start(client, h, hid)
    new = start(client, h, hid)
    assert write(client, h, hid, old, hand_trace(sd)).status_code == 409, "a newer attempt supersedes the old one"
    assert state(uid, hid) == base
    print("[PASS] reports faster than drawing, expired attempts and superseded attempts don't count")

    # ---------------------------------------------- ownership
    assert write(client, oh, hid, new, hand_trace(sd)).status_code == 404, "another learner's attempt"
    assert write(client, h, other_id, new, hand_trace(other_sd)).status_code == 404, "attempt for another character"
    assert write(client, h, hid, 999999, hand_trace(sd)).status_code == 404
    expect(client, "post", "/api/hanzi/999999/write/start", 404, headers=h)
    expect(client, "post", f"/api/hanzi/{hid}/write/start", 401)
    assert client.post(f"/api/hanzi/{hid}/write", json={"attempt_id": new, "strokes": hand_trace(sd)}).status_code == 401
    assert state(oid, hid)[0] == 0.0
    print("[PASS] attempts belong to one learner and one character (404 otherwise, 401 signed out)")

    # ---------------------------------------------- a real trace counts, once
    r = write(client, h, hid, new, hand_trace(sd, seed=3))
    assert r.status_code == 200, r.text
    assert r.json()["writing_mastery"] == 25.0 and r.json()["reaction"]["cause"] == "clean_trace", r.json()
    after = state(uid, hid)
    assert after[0] == 25.0 and after[1] == base[1] + 1 and after[2] > base[2], (after, base)
    assert write(client, h, hid, new, hand_trace(sd, seed=4)).status_code == 409, "a counted attempt can't be replayed"
    assert state(uid, hid) == after
    with SessionLocal() as db:
        a = db.get(models.HanziTraceAttempt, new)
        assert a.status == "counted" and a.total_mistakes == 0
    print("[PASS] a real drawn trace counts (+25, clean) and its attempt can't be replayed")

    # mistakes are the server's count: 3 misses before the strokes -> shaky (+8), into Review
    r = trace(client, h, hid, mistakes=3, seed=5)
    assert r.status_code == 200 and r.json()["writing_mastery"] == 33.0, r.text
    assert r.json()["reaction"]["cause"] == "shaky_trace"
    with SessionLocal() as db:
        assert db.query(models.HanziTraceAttempt).filter_by(user_id=uid, status="counted").order_by(
            models.HanziTraceAttempt.id.desc()).first().total_mistakes == 3
        assert db.query(models.LearningMistake).filter_by(user_id=uid, mistake_type="hanzi_write").count() == 1
    print("[PASS] the server counts the misses itself (3 -> +8 and a Review item)")

    # ---------------------------------------------- forged requests can't push it further
    before = state(uid, hid)
    for _ in range(10):
        aid = start(client, h, hid)
        write(client, h, hid, aid, [{"points": scribble, "matched": True}] * n)
        client.post(f"/api/hanzi/{hid}/write", headers=h, json={"attempt_id": aid, "total_mistakes": 0, "writing_mastery": 100})
    assert state(uid, hid) == before, (state(uid, hid), before)
    print("[PASS] 20 more forged requests leave writing mastery, Learning DNA and XP unchanged")

    # ---------------------------------------------- a real stroke drawn by hand passes, a mangled one doesn't
    import random
    from app.services.stroke_match import medians_of, stroke_matches
    meds = medians_of(sd)
    rng = random.Random(11)
    assert stroke_matches([tuple(p) for p in hand_stroke(sd["medians"][0], rng)], meds, 0)
    assert not stroke_matches([tuple(p) for p in hand_stroke(sd["medians"][0], rng)][::-1], meds, 0), "drawn backwards"
    assert not stroke_matches([(x + 300, y) for x, y in hand_stroke(sd["medians"][0], rng)], meds, 0), "far off"
    print("[PASS] matcher: a hand-drawn first stroke matches; backwards or shifted ones don't")

print("ALL HANZI TRACE TESTS PASSED")
