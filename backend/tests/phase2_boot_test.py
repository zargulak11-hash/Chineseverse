import os

os.environ["DATABASE_URL"] = "sqlite:///./_e2e_test.db"

import sys
import time

if os.path.exists("./_e2e_test.db"):
    os.remove("./_e2e_test.db")

from fastapi.testclient import TestClient

from app.main import app


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}")
    if not condition:
        sys.exit(1)


with TestClient(app) as client:
    r = client.get("/health")
    check("health", r.status_code == 200)

    r = client.get("/api/animals")
    check("animals seeded (20)", r.status_code == 200 and len(r.json()) == 20)

    r = client.get("/api/hsk/levels")
    check("hsk levels (1-6 + the 7-9 band)", r.status_code == 200 and len(r.json()) == 7)

    r = client.get("/api/hsk/skills")
    check("skills (9)", r.status_code == 200 and len(r.json()) == 9)

    r = client.get("/api/world/locations")
    check("old World map endpoint removed", r.status_code == 404)

    r = client.get("/api/world/scenarios/ordering-noodles")
    check("scenario detail dialogues", r.status_code == 200 and len(r.json()["dialogues"]) == 4)

    # Register
    r = client.post("/api/auth/register", json={
        "username": "e2euser", "email": "e2e@example.com", "password": "secret123",
        "native_language": "English", "daily_goal_minutes": 10,
    })
    check("register -> token", r.status_code == 201 and r.json().get("access_token"))
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    r = client.get("/api/me", headers=h)
    check("me endpoint", r.status_code == 200 and r.json()["user"]["username"] == "e2euser")
    if r.status_code != 200:
        print("   me body:", r.text[:300])

    # Choose animal
    animals = client.get("/api/animals").json()
    fox = next(a for a in animals if a["slug"] == "fox")
    r = client.post("/api/me/animal", json={"animal_id": fox["id"]}, headers=h)
    check("choose animal -> bond", r.status_code == 200 and r.json()["bond_level"] == 1)

    # Ping streak
    r = client.post("/api/me/ping", headers=h)
    check("ping streak", r.status_code == 200 and r.json()["streak"]["current_streak"] == 1)

    # Vocab list + review
    r = client.get("/api/vocab?hsk_level=1", headers=h)
    check("vocab hsk1", r.status_code == 200 and len(r.json()) > 20)
    word_id = r.json()[0]["id"]
    r = client.post(f"/api/vocab/{word_id}/review", json={"correct": True, "delta": 30}, headers=h)
    check("self-graded vocab review is gone", r.status_code in (404, 405))
    r = client.post("/api/practice/sessions", json={"source": "vocab", "hsk_level": 1, "size": 4}, headers=h)
    check("graded vocab practice", r.status_code == 201 and len(r.json()["questions"]) == 4)

    # Voice attempt
    r = client.post("/api/voice/attempt", json={
        "spoken_text": "我要一碗牛肉面",
        "expected_keywords": ["牛肉面", "一碗"],
        "scenario_id": None, "dialogue_id": None,
    }, headers=h)
    check("voice attempt", r.status_code == 200 and r.json()["attempt"]["overall"] > 0)
    check("voice reaction present", bool(r.json()["reaction"]))

    # Quests
    r = client.get("/api/quests/today", headers=h)
    check("daily quests", r.status_code == 200 and 0 < len(r.json()) <= 6)

    # DNA + dashboard
    r = client.get("/api/dna", headers=h)
    check("dna", r.status_code == 200 and r.json()["overall"] >= 0)
    r = client.get("/api/dashboard", headers=h)
    check("dashboard", r.status_code == 200 and r.json()["user"]["username"] == "e2euser")

    # Missions
    r = client.get("/api/missions", headers=h)
    check("missions list", r.status_code == 200 and len(r.json()) >= 5)
    mission_id = r.json()[0]["mission"]["id"]
    r = client.post(f"/api/missions/{mission_id}/accept", headers=h)
    check("mission accept", r.status_code == 200)

    # Achievements
    r = client.get("/api/achievements", headers=h)
    check("achievements", r.status_code == 200 and len(r.json()) >= 10)

    # Real 1-vs-1 duel between two registered users
    r = client.post("/api/auth/register", json={"username": "boot_duel_rival", "email": "boot_duel_rival@example.com", "password": "secret1"})
    rival_id, rh = r.json()["user"]["id"], {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = client.post("/api/duels", json={"opponent_id": rival_id, "hsk_level": 1}, headers=h)
    check("duel create (pending challenge)", r.status_code == 201 and r.json()["status"] == "pending")
    duel_id = r.json()["id"]
    r = client.post(f"/api/duels/{duel_id}/accept", headers=rh)
    check("duel accept", r.status_code == 200 and r.json()["status"] == "active")
    for hh in (h, rh):
        state = client.post(f"/api/duels/{duel_id}/start", headers=hh).json()
        while state["current"] is not None:
            q = state["current"]
            state = client.post(f"/api/duels/{duel_id}/answer", json={"index": q["index"], "choice_id": q["options"][0]["id"]}, headers=hh).json()["duel"]
    r = client.get(f"/api/duels/{duel_id}", headers=h)
    check("duel finish", r.status_code == 200 and r.json()["status"] == "completed" and r.json()["result"] is not None)

    # Case solve
    r = client.get("/api/world/scenarios/the-missing-bill")
    check("case scenario exists", r.status_code == 200 and r.json()["is_case"] is True)
    r = client.post("/api/world/scenarios/the-missing-bill/solve",
                    json={"conclusion": "顾客给了二十五元"}, headers=h)
    check("case solve correct", r.status_code == 200 and r.json()["solved"] is True)
    r = client.post("/api/world/scenarios/the-missing-bill/solve",
                    json={"conclusion": "老板说对了"}, headers=h)
    check("case solve wrong", r.status_code == 200 and r.json()["solved"] is False)

    # Login again
    r = client.post("/api/auth/login", json={"username": "e2euser", "password": "secret123"})
    check("login", r.status_code == 200 and r.json().get("access_token"))

print("\nAll E2E boot checks passed.")