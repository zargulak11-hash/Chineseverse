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
    check("animals seeded (16)", r.status_code == 200 and len(r.json()) == 16)

    r = client.get("/api/hsk/levels")
    check("hsk levels (6)", r.status_code == 200 and len(r.json()) == 6)

    r = client.get("/api/hsk/skills")
    check("skills (9)", r.status_code == 200 and len(r.json()) == 9)

    r = client.get("/api/world/locations")
    check("locations (9)", r.status_code == 200 and len(r.json()) == 9)

    r = client.get("/api/world/locations/restaurant")
    check("location detail w/ scenarios", r.status_code == 200 and len(r.json()["scenarios"]) >= 2)

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
    check("vocab review", r.status_code == 200 and r.json()["mastery"] > 0 and r.json()["status"] in ("learning", "reviewing"))

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

    # Duel vs Buddy
    r = client.post("/api/duels", json={"opponent_username": "Buddy"}, headers=h)
    check("duel create", r.status_code == 201 and len(r.json()["questions"]) == 5)
    duel_id = r.json()["id"]
    q0 = r.json()["questions"][0]
    r = client.post(f"/api/duels/{duel_id}/answer", json={
        "index": 0, "answer": q0["options"][0], "response_time_ms": 1200,
    }, headers=h)
    check("duel answer", r.status_code == 200 and "my_score" in r.json())
    r = client.post(f"/api/duels/{duel_id}/finish", headers=h)
    check("duel finish", r.status_code == 200 and r.json()["finished"] is True)

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