"""Missions (routers/missions.py, gamification.progress_missions): accept
works for every unlocked mission, locked ones stay locked, and progress
only ever comes from real activity graded on the server. (AI is offline in
tests: deterministic speech grading.)"""

import pytest

from app import models
from app.database import SessionLocal
from app.services.gamification import progress_missions
from helpers import expect, register, unique_name

VOICE = {"spoken_text": "请问火车站怎么走？", "response_time_ms": 1500}


def by_slug(client, h):
    return {m["mission"]["slug"]: m for m in expect(client, "get", "/api/missions", 200, headers=h)}


@pytest.fixture
def learner(client):
    return register(client, unique_name("missions"))


def correct_answers(client, h, n):
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "vocab", "hsk_level": 1, "size": max(n, 4)})
    with SessionLocal() as db:
        stored = db.get(models.PracticeSession, s["id"]).questions
    for i in range(n):
        expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=h,
               json={"index": i, "choice_id": stored[i]["item_id"]})
    return s, stored


def test_missions_say_where_they_are_done_and_which_are_locked(client, learner):
    _, h = learner
    ms = by_slug(client, h)
    assert len(ms) >= 10
    assert ms["solve-case"]["locked"] and ms["fruit-shop"]["locked"], "HSK 2 missions are locked at HSK 1"
    assert not ms["directions-master"]["locked"]
    assert ms["directions-master"]["mission"]["scenario_slug"] == "asking-directions"
    assert ms["solve-case"]["mission"]["scenario_type"] == "case"


def test_accepting_a_scenario_mission_activates_it_and_a_locked_one_is_403(client, learner):
    # Accept used to be a no-op for every mission tied to a scenario.
    _, h = learner
    ms = by_slug(client, h)
    a = expect(client, "post", f"/api/missions/{ms['directions-master']['mission']['id']}/accept", 200, headers=h)
    assert a["status"] == "active", a["status"]
    expect(client, "post", f"/api/missions/{ms['solve-case']['mission']['id']}/accept", 403, headers=h)
    expect(client, "post", "/api/missions/999999/accept", 404, headers=h)
    expect(client, "post", f"/api/missions/{ms['first-duel']['mission']['id']}/accept", 401)


def test_the_browser_cannot_complete_a_mission(client, learner):
    _, h = learner
    wc_id = by_slug(client, h)["word-collector"]["mission"]["id"]
    for body in ({"status": "completed"}, {"delta": 100}):
        r = client.post(f"/api/missions/{wc_id}/progress", headers=h, json=body)
        assert r.status_code in (404, 405), r.status_code
    assert by_slug(client, h)["word-collector"]["status"] != "completed"
    # the self-graded vocabulary endpoint that used to feed it is gone too
    assert client.post("/api/vocab/1/review", headers=h, json={"correct": True}).status_code in (404, 405)


def test_ten_correct_graded_answers_complete_word_collector_once(client, learner):
    uid, h = learner
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
    s2, st2 = correct_answers(client, h, 1)
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


def test_mission_progress_is_per_learner(client, learner):
    _, h = learner
    correct_answers(client, h, 4)
    _, oh = register(client, unique_name("othermissions"))
    assert by_slug(client, h)["word-collector"]["progress"] == 4
    assert by_slug(client, oh)["word-collector"]["progress"] == 0


def test_a_conversation_mission_completes_on_its_last_line_answered_correctly(client, learner):
    _, h = learner
    expect(client, "post", f"/api/missions/{by_slug(client, h)['directions-master']['mission']['id']}/accept", 200, headers=h)
    with SessionLocal() as db:
        sc = db.query(models.Scenario).filter_by(slug="asking-directions").one()
        turns = (db.query(models.Dialogue).filter_by(scenario_id=sc.id, speaker="learner")
                 .order_by(models.Dialogue.turn_index).all())
        sc_id, first_turn, last_turn = sc.id, turns[0].id, turns[-1].id
        last_answer = "".join(turns[-1].expected_keywords or [])
    assert first_turn != last_turn
    assert last_answer, "the last line has real expected words"
    voice = {**VOICE, "scenario_id": sc_id}
    expect(client, "post", "/api/voice/attempt", 200, headers=h, json={**voice, "dialogue_id": first_turn})
    assert by_slug(client, h)["directions-master"]["status"] == "active"
    # a wrong answer to the last line -- even naming its own "expected" words -- doesn't complete it
    expect(client, "post", "/api/voice/attempt", 200, headers=h,
           json={**voice, "spoken_text": "你好", "expected_keywords": ["你好"], "dialogue_id": last_turn})
    assert by_slug(client, h)["directions-master"]["status"] == "active"
    expect(client, "post", "/api/voice/attempt", 200, headers=h,
           json={**voice, "spoken_text": last_answer, "dialogue_id": last_turn})
    assert by_slug(client, h)["directions-master"]["status"] == "completed"


def test_a_mission_above_the_learners_level_does_not_advance(client, learner):
    uid, h = learner
    with SessionLocal() as db:
        fruit = db.query(models.Scenario).filter_by(slug="buying-fruit").one()
        fturn = (db.query(models.Dialogue).filter_by(scenario_id=fruit.id, speaker="learner")
                 .order_by(models.Dialogue.turn_index.desc()).first())
        fruit_id, fturn_id = fruit.id, fturn.id
    # The location is still locked for an HSK 1 learner, so the turn itself is refused...
    expect(client, "post", "/api/voice/attempt", 403, headers=h,
           json={**VOICE, "scenario_id": fruit_id, "dialogue_id": fturn_id})
    # ...and the mission engine skips locked missions on its own too.
    with SessionLocal() as db:
        progress_missions(db, db.get(models.User, uid), "conversation", scenario_id=fruit_id)
        db.commit()
    fb = by_slug(client, h)["fruit-shop"]
    assert fb["status"] != "completed" and fb["progress"] == 0 and fb["locked"], fb
