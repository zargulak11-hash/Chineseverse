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

    # real activity moves it: 10 vocabulary reviews -> Word Collector, rewards granted
    with SessionLocal() as db:
        xp_before = db.get(models.User, uid).total_xp
        words = [w.id for w in db.query(models.VocabularyWord).limit(10)]
    for wid in words:
        expect(client, "post", f"/api/vocab/{wid}/review", 200, headers=h, json={"correct": True})
    wc = by_slug(client, h)["word-collector"]
    assert wc["status"] == "completed" and wc["progress"] == 10, wc
    with SessionLocal() as db:
        assert db.get(models.User, uid).total_xp >= xp_before + wc["mission"]["reward_xp"]
    print("[PASS] 10 real vocabulary reviews complete Word Collector and grant its reward")

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
