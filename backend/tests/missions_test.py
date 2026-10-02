"""Missions (routers/missions.py, gamification.progress_missions) on a fresh
database: accept works for every unlocked mission, locked ones stay locked,
progress only ever comes from real activity on the server."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/missions.db"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, f"{method.upper()} {url} -> {resp.status_code} (expected {expected}): {resp.text[:300]}"
    return resp.json() if resp.content else None


def register(client, name):
    data = expect(client, "post", "/api/auth/register", 201,
                  json={"username": name, "email": f"{name}@example.com", "password": "secret1"})
    return data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}


def by_slug(client, h):
    return {m["mission"]["slug"]: m for m in expect(client, "get", "/api/missions", 200, headers=h)}


with TestClient(app) as client:
    uid, h = register(client, "missionlearner")
    ms = by_slug(client, h)
    assert len(ms) >= 10
    assert ms["solve-case"]["locked"] and ms["fruit-shop"]["locked"], "HSK 2 missions are locked at HSK 1"
    assert not ms["directions-master"]["locked"]
    assert ms["directions-master"]["mission"]["scenario_slug"] == "asking-directions"
    assert ms["solve-case"]["mission"]["scenario_type"] == "case"
    print("[PASS] missions list where each is done (scenario slug/type) and which are locked above the learner's HSK")

    # accept used to be a no-op for every mission tied to a scenario
    a = expect(client, "post", f"/api/missions/{ms['directions-master']['mission']['id']}/accept", 200, headers=h)
    assert a["status"] == "active", a["status"]
    expect(client, "post", f"/api/missions/{ms['solve-case']['mission']['id']}/accept", 403, headers=h)
    expect(client, "post", "/api/missions/999999/accept", 404, headers=h)
    expect(client, "post", f"/api/missions/{ms['first-duel']['mission']['id']}/accept", 401)
    print("[PASS] accepting a scenario mission activates it; a locked one is 403")

    # the client can no longer complete a mission itself
    for body in ({"status": "completed"}, {"delta": 100}):
        r = client.post(f"/api/missions/{ms['word-collector']['mission']['id']}/progress", headers=h, json=body)
        assert r.status_code in (404, 405), r.status_code
    assert by_slug(client, h)["word-collector"]["status"] != "completed"
    print("[PASS] POST /missions/{id}/progress is gone: a mission cannot be completed from the browser")

    # the self-graded vocabulary endpoint that used to feed it is gone too
    assert client.post("/api/vocab/1/review", headers=h, json={"correct": True}).status_code in (404, 405)

    # real activity moves it: 10 correct graded vocabulary answers -> Word Collector, reward granted
    with SessionLocal() as db:
        xp_before = db.get(models.User, uid).total_xp
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "vocab", "hsk_level": 1, "size": 10})
    with SessionLocal() as db:
        stored = db.get(models.PracticeSession, s["id"]).questions
    assert len(stored) == 10
    wrong = next(o["id"] for o in s["questions"][0]["options"] if o["id"] != stored[0]["item_id"])
    expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h, json={"index": 0, "choice_id": wrong})
    assert by_slug(client, h)["word-collector"]["progress"] == 0, "a wrong answer does not count"
    for i in range(1, 10):
        expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
               json={"index": i, "choice_id": stored[i]["item_id"]})
    assert by_slug(client, h)["word-collector"]["progress"] == 9
    s2 = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "vocab", "hsk_level": 1, "size": 4})
    with SessionLocal() as db:
        st2 = db.get(models.PracticeSession, s2["id"]).questions
    expect(client, "post", f"/api/practice/sessions/{s2['id']}/answer", 200, headers=h, json={"index": 0, "choice_id": st2[0]["item_id"]})
    wc = by_slug(client, h)["word-collector"]
    assert wc["status"] == "completed" and wc["progress"] == 10, wc
    with SessionLocal() as db:
        assert db.get(models.User, uid).total_xp >= xp_before + wc["mission"]["reward_xp"]
    # finishing it again does not pay twice
    def wc_row():
        with SessionLocal() as db:
            m = db.query(models.Mission).filter_by(slug="word-collector").one()
            um = db.query(models.UserMission).filter_by(user_id=uid, mission_id=m.id).one()
            return um.status, um.progress, um.completed_at
    done = wc_row()
    expect(client, "post", f"/api/practice/sessions/{s2['id']}/answer", 200, headers=h, json={"index": 1, "choice_id": st2[1]["item_id"]})
    assert wc_row() == done, (wc_row(), done)
    print("[PASS] 10 correct graded vocabulary answers complete Word Collector once (wrong answers don't count)")

    # another learner's activity never touches this learner's missions
    oid, oh = register(client, "othermissionlearner")
    assert by_slug(client, oh)["word-collector"]["progress"] == 0
    print("[PASS] mission progress is per learner")

    # a conversation mission completes on the conversation's last learner line, not the first
    with SessionLocal() as db:
        sc = db.query(models.Scenario).filter_by(slug="asking-directions").one()
        turns = (db.query(models.Dialogue).filter_by(scenario_id=sc.id, speaker="learner")
                 .order_by(models.Dialogue.turn_index).all())
        sc_id = sc.id
        first_turn, last_turn = turns[0].id, turns[-1].id
    assert first_turn != last_turn
    voice = {"spoken_text": "请问火车站怎么走？", "scenario_id": sc_id, "response_time_ms": 1500}
    expect(client, "post", "/api/voice/attempt", 200, headers=h, json={**voice, "dialogue_id": first_turn})
    assert by_slug(client, h)["directions-master"]["status"] == "active"
    expect(client, "post", "/api/voice/attempt", 200, headers=h, json={**voice, "dialogue_id": last_turn})
    assert by_slug(client, h)["directions-master"]["status"] == "completed"
    print("[PASS] 'Getting Around' completes on the scenario's last learner line, not on the first one")

    # a locked mission does not advance even when its activity happens
    with SessionLocal() as db:
        fruit = db.query(models.Scenario).filter_by(slug="buying-fruit").one()
        fturn = (db.query(models.Dialogue).filter_by(scenario_id=fruit.id, speaker="learner")
                 .order_by(models.Dialogue.turn_index.desc()).first())
        fruit_id, fturn_id = fruit.id, fturn.id
    # The location is still locked for an HSK 1 learner, so the turn itself is refused...
    expect(client, "post", "/api/voice/attempt", 403, headers=h,
           json={**voice, "scenario_id": fruit_id, "dialogue_id": fturn_id})
    # ...and the mission engine skips locked missions on its own too.
    from app.services.gamification import progress_missions
    with SessionLocal() as db:
        progress_missions(db, db.get(models.User, uid), "conversation", scenario_id=fruit_id)
        db.commit()
    fb = by_slug(client, h)["fruit-shop"]
    assert fb["status"] != "completed" and fb["progress"] == 0 and fb["locked"], fb
    print("[PASS] a mission above the learner's HSK level does not advance")

print("ALL MISSION TESTS PASSED")
