"""Hanzi stroke tracing is checked on the server (services/stroke_match.py,
routers/hanzi.py): forged results, replays, foreign attempts and drawings
that aren't the character never move writing mastery; a real trace does."""

import random
from types import SimpleNamespace

import pytest

from app import models
from app.database import SessionLocal
from app.services.stroke_match import medians_of, stroke_matches
from helpers import expect, register, unique_name
from trace_helpers import hand_stroke, hand_trace, start, stroke_data, trace

SCRIBBLE = [[100.0, 100.0], [120.0, 140.0], [160.0, 120.0]]


def state(uid, hid):
    with SessionLocal() as db:
        rec = db.query(models.UserHanzi).filter_by(user_id=uid, hanzi_id=hid).first()
        u = db.get(models.User, uid)
        writing = next((s.mastery for s in u.user_skills if s.skill and s.skill.code == "writing"), 0.0)
        return ((rec.writing_mastery or 0.0) if rec else 0.0, (rec.times_written or 0) if rec else 0, writing, u.total_xp)


def write(client, h, hid, aid, strokes):
    return client.post(f"/api/hanzi/{hid}/write", headers=h, json={"attempt_id": aid, "strokes": strokes})


@pytest.fixture(scope="module")
def chars(client):
    with SessionLocal() as db:
        hz = db.query(models.Hanzi).filter(models.Hanzi.character == "好").first()
        other = db.query(models.Hanzi).filter(models.Hanzi.character == "人").first()
        hid, other_id, n = hz.id, other.id, len(hz.stroke_data["medians"])
    return SimpleNamespace(hid=hid, other_id=other_id, n=n, sd=stroke_data(hid), other_sd=stroke_data(other_id))


@pytest.fixture
def tracer(client, chars):
    """A learner with skill rows, and their untouched state for 好."""
    uid, h = register(client, unique_name("tracer"))
    expect(client, "get", "/api/dashboard", 200, headers=h)
    return SimpleNamespace(uid=uid, h=h, base=state(uid, chars.hid))


def test_forged_results_from_the_browser_change_nothing(client, chars, tracer):
    forged = [
        {"total_mistakes": 0},
        {"total_mistakes": 0, "correct": True, "completed": True, "mastery": 100, "writing_mastery": 100, "score": 100, "xp": 999},
        {"correct": True},
        {"completed": True, "strokes_completed": chars.n},
    ]
    for _ in range(5):
        for body in forged:
            r = client.post(f"/api/hanzi/{chars.hid}/write", headers=tracer.h, json=body)
            assert r.status_code == 422, (body, r.status_code)
    assert state(tracer.uid, chars.hid) == tracer.base


INVALID_DRAWINGS = {
    "scribbles claimed as correct": lambda c: [{"points": SCRIBBLE, "matched": True}] * c.n,
    "only half the strokes": lambda c: hand_trace(c.sd)[: c.n // 2],
    "strokes out of order": lambda c: [hand_trace(c.sd)[1], hand_trace(c.sd)[0]] + hand_trace(c.sd)[2:],
    "another character's strokes": lambda c: (hand_trace(c.other_sd)[: c.n]
                                              if len(c.other_sd["medians"]) >= c.n else hand_trace(c.other_sd)),
    "strokes after the character was complete": lambda c: hand_trace(c.sd) + [{"points": SCRIBBLE, "matched": False}],
    "points far outside the box": lambda c: [{"points": [[99999.0, 5.0], [100000.0, 6.0]], "matched": True}] + hand_trace(c.sd)[1:],
    "only misses": lambda c: [{"points": SCRIBBLE, "matched": False}] * 3,
    "exact median vertices of another stroke": lambda c: (
        [{"points": [list(p) for p in c.sd["medians"][-1]], "matched": True}] + hand_trace(c.sd)[1:]),
}


@pytest.mark.parametrize("label", list(INVALID_DRAWINGS))
def test_an_invalid_drawing_is_rejected_and_spends_the_attempt(client, chars, tracer, label):
    aid = start(client, tracer.h, chars.hid)
    r = write(client, tracer.h, chars.hid, aid, INVALID_DRAWINGS[label](chars))
    assert r.status_code == 422, (label, r.status_code, r.text)
    assert r.json()["detail"].startswith("Trace not accepted"), r.json()
    # the attempt is spent: the forger can't retry on it
    assert write(client, tracer.h, chars.hid, aid, hand_trace(chars.sd)).status_code == 409
    assert state(tracer.uid, chars.hid) == tracer.base


def test_malformed_stroke_lists_are_rejected(client, chars, tracer):
    for bad in ([], [{"points": [[1.0, 2.0]], "matched": True}]):
        aid = start(client, tracer.h, chars.hid)
        assert write(client, tracer.h, chars.hid, aid, bad).status_code == 422
    assert state(tracer.uid, chars.hid) == tracer.base


def test_too_fast_expired_and_superseded_attempts_do_not_count(client, chars, tracer):
    h, hid, sd = tracer.h, chars.hid, chars.sd
    aid = expect(client, "post", f"/api/hanzi/{hid}/write/start", 201, headers=h)["attempt_id"]
    r = write(client, h, hid, aid, hand_trace(sd))
    assert r.status_code == 422 and "faster" in r.json()["detail"], r.text
    aid = start(client, h, hid, seconds_ago=31 * 60)
    assert write(client, h, hid, aid, hand_trace(sd)).status_code == 409
    old = start(client, h, hid)
    start(client, h, hid)
    assert write(client, h, hid, old, hand_trace(sd)).status_code == 409, "a newer attempt supersedes the old one"
    assert state(tracer.uid, hid) == tracer.base


def test_attempts_belong_to_one_learner_and_one_character(client, chars, tracer):
    h, hid, sd = tracer.h, chars.hid, chars.sd
    oid, oh = register(client, unique_name("othertracer"))
    attempt = start(client, h, hid)
    assert write(client, oh, hid, attempt, hand_trace(sd)).status_code == 404, "another learner's attempt"
    assert write(client, h, chars.other_id, attempt, hand_trace(chars.other_sd)).status_code == 404, "attempt for another character"
    assert write(client, h, hid, 999999, hand_trace(sd)).status_code == 404
    expect(client, "post", "/api/hanzi/999999/write/start", 404, headers=h)
    expect(client, "post", f"/api/hanzi/{hid}/write/start", 401)
    assert client.post(f"/api/hanzi/{hid}/write", json={"attempt_id": attempt, "strokes": hand_trace(sd)}).status_code == 401
    assert state(oid, hid)[0] == 0.0


def test_a_real_trace_counts_once_and_the_server_counts_the_misses(client, chars, tracer):
    h, hid, sd, base = tracer.h, chars.hid, chars.sd, tracer.base
    attempt = start(client, h, hid)
    r = write(client, h, hid, attempt, hand_trace(sd, seed=3))
    assert r.status_code == 200, r.text
    assert r.json()["writing_mastery"] == 25.0 and r.json()["reaction"]["cause"] == "clean_trace", r.json()
    after = state(tracer.uid, hid)
    assert after[0] == 25.0 and after[1] == base[1] + 1 and after[2] > base[2], (after, base)
    assert write(client, h, hid, attempt, hand_trace(sd, seed=4)).status_code == 409, "a counted attempt can't be replayed"
    assert state(tracer.uid, hid) == after
    with SessionLocal() as db:
        a = db.get(models.HanziTraceAttempt, attempt)
        assert a.status == "counted" and a.total_mistakes == 0

    # 3 misses before the strokes -> shaky (+8), and a Review item
    r = trace(client, h, hid, mistakes=3, seed=5)
    assert r.status_code == 200 and r.json()["writing_mastery"] == 33.0, r.text
    assert r.json()["reaction"]["cause"] == "shaky_trace"
    with SessionLocal() as db:
        assert db.query(models.HanziTraceAttempt).filter_by(user_id=tracer.uid, status="counted").order_by(
            models.HanziTraceAttempt.id.desc()).first().total_mistakes == 3
        assert db.query(models.LearningMistake).filter_by(user_id=tracer.uid, mistake_type="hanzi_write").count() == 1

    # 20 more forged requests leave writing mastery, Learning DNA and XP unchanged
    before = state(tracer.uid, hid)
    for _ in range(10):
        aid = start(client, h, hid)
        write(client, h, hid, aid, [{"points": SCRIBBLE, "matched": True}] * chars.n)
        client.post(f"/api/hanzi/{hid}/write", headers=h, json={"attempt_id": aid, "total_mistakes": 0, "writing_mastery": 100})
    assert state(tracer.uid, hid) == before


def test_matcher_accepts_a_hand_drawn_stroke_but_not_a_mangled_one(chars):
    meds = medians_of(chars.sd)
    rng = random.Random(11)
    first = chars.sd["medians"][0]
    assert stroke_matches([tuple(p) for p in hand_stroke(first, rng)], meds, 0)
    assert not stroke_matches([tuple(p) for p in hand_stroke(first, rng)][::-1], meds, 0), "drawn backwards"
    assert not stroke_matches([(x + 300, y) for x, y in hand_stroke(first, rng)], meds, 0), "far off"
