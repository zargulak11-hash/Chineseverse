"""A freshly booted API serves its seeded content and a new learner can
walk the core loop once across the main features (a broad smoke check;
each feature has its own detailed module)."""

import pytest

from helpers import bearer, expect, register


def test_health_and_seeded_public_content(client):
    expect(client, "get", "/health", 200)
    assert len(expect(client, "get", "/api/animals", 200)) == 20
    assert len(expect(client, "get", "/api/hsk/levels", 200)) == 7  # 1-6 + the 7-9 band
    assert len(expect(client, "get", "/api/hsk/skills", 200)) == 9
    expect(client, "get", "/api/world/locations", 404)  # the old World map endpoint is removed
    assert len(expect(client, "get", "/api/world/scenarios/ordering-noodles", 200)["dialogues"]) == 4
    assert expect(client, "get", "/api/world/scenarios/the-missing-bill", 200)["is_case"] is True


@pytest.fixture(scope="module")
def booted(client):
    data = expect(client, "post", "/api/auth/register", 201, json={
        "username": "e2euser", "email": "e2e@example.com", "password": "secret123",
        "native_language": "English", "daily_goal_minutes": 10,
    })
    assert data["access_token"]
    return bearer(data["access_token"])


def test_a_new_learner_signs_in_and_sets_up(client, booted):
    h = booted
    assert expect(client, "get", "/api/me", 200, headers=h)["user"]["username"] == "e2euser"
    fox = next(a for a in expect(client, "get", "/api/animals", 200) if a["slug"] == "fox")
    assert expect(client, "post", "/api/me/animal", 200, json={"animal_id": fox["id"]}, headers=h)["bond_level"] == 1
    assert expect(client, "post", "/api/me/ping", 200, headers=h)["streak"]["current_streak"] == 1
    assert expect(client, "post", "/api/auth/login", 200, json={"username": "e2euser", "password": "secret123"})["access_token"]


def test_core_learning_endpoints_answer_for_a_new_learner(client, booted):
    h = booted
    words = expect(client, "get", "/api/vocab?hsk_level=1", 200, headers=h)
    assert len(words) > 20
    assert client.post(f"/api/vocab/{words[0]['id']}/review", json={"correct": True, "delta": 30}, headers=h).status_code in (404, 405)
    s = expect(client, "post", "/api/practice/sessions", 201, json={"source": "vocab", "hsk_level": 1, "size": 4}, headers=h)
    assert len(s["questions"]) == 4
    v = expect(client, "post", "/api/voice/attempt", 200, headers=h, json={
        "spoken_text": "我要一碗牛肉面", "expected_keywords": ["牛肉面", "一碗"], "scenario_id": None, "dialogue_id": None,
    })
    assert v["attempt"]["overall"] > 0 and v["reaction"]
    assert 0 < len(expect(client, "get", "/api/quests/today", 200, headers=h)) <= 6
    assert expect(client, "get", "/api/dna", 200, headers=h)["overall"] >= 0
    assert expect(client, "get", "/api/dashboard", 200, headers=h)["user"]["username"] == "e2euser"
    missions = expect(client, "get", "/api/missions", 200, headers=h)
    assert len(missions) >= 5
    expect(client, "post", f"/api/missions/{missions[0]['mission']['id']}/accept", 200, headers=h)
    assert len(expect(client, "get", "/api/achievements", 200, headers=h)) >= 10


def test_a_duel_between_two_new_learners_finishes_with_a_result(client, booted):
    h = booted
    rival_id, rh = register(client, "boot_duel_rival")
    d = expect(client, "post", "/api/duels", 201, json={"opponent_id": rival_id, "hsk_level": 1}, headers=h)
    assert d["status"] == "pending"
    assert expect(client, "post", f"/api/duels/{d['id']}/accept", 200, headers=rh)["status"] == "active"
    for hh in (h, rh):
        state = expect(client, "post", f"/api/duels/{d['id']}/start", 200, headers=hh)
        while state["current"] is not None:
            q = state["current"]
            state = expect(client, "post", f"/api/duels/{d['id']}/answer", 200, headers=hh,
                           json={"index": q["index"], "choice_id": q["options"][0]["id"]})["duel"]
    done = expect(client, "get", f"/api/duels/{d['id']}", 200, headers=h)
    assert done["status"] == "completed" and done["result"] is not None


def test_a_case_is_solved_only_by_the_right_conclusion(client, booted):
    h = booted
    right = expect(client, "post", "/api/world/scenarios/the-missing-bill/solve", 200, headers=h,
                   json={"conclusion": "顾客给了二十五元"})
    assert right["solved"] is True
    wrong = expect(client, "post", "/api/world/scenarios/the-missing-bill/solve", 200, headers=h,
                   json={"conclusion": "老板说对了"})
    assert wrong["solved"] is False
