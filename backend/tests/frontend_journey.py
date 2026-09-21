"""Simulates the HTTP calls the PHASE 2 React pages make against the live
stack. Requests go through the Vite dev proxy (localhost:5173 -> backend),
so this is a true end-to-end check of SPA client -> proxy -> FastAPI -> DB."""

import argparse
import io
import sys

import httpx

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser()
parser.add_argument("--base", default="http://localhost:5173")
args = parser.parse_args()

c = httpx.Client(base_url=args.base, timeout=30)


def call(method, path, body=None, headers=None, expected=(200, 201)):
    r = c.request(method, path, json=body, headers=headers or {})
    ok = r.status_code in expected
    label = f"{method} {path}"
    if not ok:
        print(f"  FAIL {label} -> {r.status_code}: {r.text[:300]}")
        raise SystemExit(1)
    print(f"  OK {label} -> {r.status_code}")
    return r.json() if r.text else None


print("== Landing: public pages ==")
r = c.get("/")
assert "<title>LinguaVerse</title>" in r.text
print("  OK SPA root served")
animals = call("GET", "/api/animals")
assert len(animals) == 16, f"expected 16 animals, got {len(animals)}"
assert any(a["slug"] == "panda" for a in animals)
print(f"  OK 16 animals listed (panda present)")

print("\n== Register (POST /api/auth/register) ==")
import uuid

uname = "journey" + uuid.uuid4().hex[:6]
user = call(
    "POST",
    "/api/auth/register",
    {"username": uname, "email": f"{uname}@example.com", "password": "secret1"},
    expected=(201, 200),
)
tok = user["access_token"]
H = {"Authorization": f"Bearer {tok}"}
assert user["user"]["username"] == uname
print("  OK token issued")

print("\n== Animal selection (POST /api/me/animal) ==")
fox = next(a for a in animals if a["slug"] == "fox")
call("POST", "/api/me/animal", {"animal_id": fox["id"]}, headers=H)

print("\n== Dashboard (GET /api/dashboard) ==")
dash = call("GET", "/api/dashboard", headers=H)
assert dash["animal"]["slug"] == "fox"
assert dash["hsk_level"] == 1
assert dash["quests_today"] and isinstance(dash["achievements"], list) and dash["recent_mistakes"] is not None
print(f"  OK animal={dash['animal']['name']} mastery={dash['mastery']:.0f}%")

print("\n== DNA (GET /api/dna) ==")
dna = call("GET", "/api/dna", headers=H)
assert len(dna["skills"]) == 9
print(f"  OK 9 skills, overall={dna['overall']:.0f}")

print("\n== HSK roadmap (GET /api/hsk/roadmap) ==")
rm = call("GET", "/api/hsk/roadmap", headers=H)
assert len(rm["levels"]) == 6 and rm["current_level"] == 1
print("  OK 6 levels")

print("\n== Lessons + progress (POST /api/progress, PATCH) ==")
lessons = call("GET", "/api/lessons", headers=H)
fl = lessons[0]
p = call("POST", "/api/progress", {"user_id": user["user"]["id"], "lesson_id": fl["id"], "status": "in_progress"}, headers=H, expected=(200, 201))
call("PATCH", f"/api/progress/{p['id']}", {"status": "completed", "score": 100}, headers=H)
print(f"  OK lesson '{fl['title']}' completed")

print("\n== Vocabulary (GET /api/vocab + POST review) ==")
words = call("GET", "/api/vocab?hsk_level=1", headers=H)
assert len(words) >= 20, f"expected >=20 HSK1 words, got {len(words)}"
call("POST", f"/api/vocab/{words[0]['id']}/review", {"correct": True}, headers=H)
print(f"  OK reviewed '{words[0]['simplified']}'")

print("\n== World (locations + scenario detail) ==")
locs = call("GET", "/api/world/locations", headers=H)
assert len(locs) == 9
rest = call("GET", "/api/world/locations/restaurant", headers=H)
assert rest["scenarios"], "restaurant should have scenarios"
print(f"  OK {len(locs)} locations, restaurant has {len(rest['scenarios'])} conversations")

print("\n== Conversation: voice attempt (POST /api/voice/attempt) ==")
sc = call("GET", "/api/world/scenarios/ordering-noodles", headers=H)
vr = call(
    "POST",
    "/api/voice/attempt",
    {
        "spoken_text": "我要一碗牛肉面",
        "prompt_text": "Say you want noodles",
        "scenario_id": sc["id"],
        "expected_keywords": ["牛肉面", "一碗"],
        "response_time_ms": 1200,
    },
    headers=H,
)
assert vr["reaction"] and "attempt" in vr
print(f"  OK reaction='{vr['reaction']}' overall={vr['attempt']['overall']:.0f}")

print("\n== Case solve (POST /api/world/scenarios/the-missing-bill/solve) ==")
wrong = call("POST", "/api/world/scenarios/the-missing-bill/solve", {"conclusion": "谁都偷了钱"}, headers=H)
right = call("POST", "/api/world/scenarios/the-missing-bill/solve", {"conclusion": "顾客是对的，他给了二十五元"}, headers=H)
assert wrong["solved"] is False and right["solved"] is True
print(f"  OK wrong={wrong['solved']} right={right['solved']}")

print("\n== Duel vs Buddy (create / answer / finish) ==")
d = call("POST", "/api/duels", {"opponent_username": "Buddy"}, headers=H)
assert d["opponent"] == "Buddy" and len(d["questions"]) == 5
for i, q in enumerate(d["questions"]):
    call("POST", f"/api/duels/{d['id']}/answer", {"index": i, "answer": (q["options"] or ["?"])[0], "response_time_ms": 900}, headers=H)
fin = call("POST", f"/api/duels/{d['id']}/finish", headers=H)
assert fin["finished"] is True and fin["opponent"] == "Buddy"
print("  OK duel finished, winner:", fin["winner"])

print("\n== Quests + claim ==")
qs = call("GET", "/api/quests/today", headers=H)
call("POST", f"/api/quests/{qs[0]['id']}/claim", headers=H)
print(f"  OK claimed quest '{qs[0]['title']}'")

print("\n== Companion free chat (POST /api/voice/evaluate) ==")
ev = call("POST", "/api/voice/evaluate", {"prompt_text": "", "spoken_text": "你好", "expected_keywords": []}, headers=H)
assert ev["reaction"] and ev["scores"]
print(f"  OK reaction='{ev['reaction']}'")

print("\n== Mistakes (GET /api/mistakes) ==")
mist = call("GET", "/api/mistakes", headers=H)
print(f"  OK {len(mist)} mistakes (includes case blunders)")

print("\n== Achievements (GET /api/achievements) ==")
ach = call("GET", "/api/achievements", headers=H)
assert len(ach) == 12
print(f"  OK {len(ach)} badges, {sum(1 for b in ach if b['unlocked'])} unlocked")

print("\n== Profile (GET /api/me + PATCH /api/me/profile) ==")
me = call("GET", "/api/me", headers=H)
call("PATCH", "/api/me/profile", {"goal_text": "旅行去北京", "daily_goal_minutes": 30}, headers=H)
print("  OK profile updated")

print("\n== Login again (POST /api/auth/login) ==")
lg = call("POST", "/api/auth/login", {"username": uname, "password": "secret1"})
assert lg["access_token"]
print("  OK re-login works")

print("\nJOURNEY TEST PASSED: frontend routes -> Vite proxy -> FastAPI -> PostgreSQL")
c.close()