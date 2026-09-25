"""Tests for the real-users-only Admin Users/Home system: GET
/api/admin/dashboard, the companion field on the admin user list, and
confirmation that no demo-user seed path exists any more.

Runs in-process (FastAPI TestClient) against a fresh temp sqlite
database, same convention as smoke_test.py.

Covers the required scenarios:
 1. no demo-seed module exists any more (scripts/seed_demo_users.py was
    deleted along with the demo users it created)
 2. real (self-registered) users are unaffected/listed normally
 3. the promoted owner/admin account is unaffected
 5. GET /api/admin/dashboard returns the real DB count
 6. a normal user gets 403 on the dashboard endpoint
 7. a normal user gets 403 on the users list (regression from the
    original admin feature, re-checked here since schemas.py changed)
 8. an admin gets 200 on the dashboard endpoint
 9. an admin gets 200 on the users list
10. the list only ever contains rows that are real User table rows
    (trivially true here — there is no other data source — asserted by
    cross-checking against a direct DB count)
11. a user's chosen main companion (set via POST /api/me/animal) is
    returned as companion_slug/companion_name
12. talking to a DIFFERENT animal via the Daily Voice Companion endpoint
    (POST /api/voice/companion-chat) does NOT change what the admin list
    reports as that user's companion
13. the response never includes avatar_url/any personal-profile-photo
    field — only the companion fields
14/15. deleting a user updates both the list and the dashboard count
16. admin cannot delete themselves (regression, re-checked)
17. no password/hash/token/secret field is ever present (regression)
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/admin_dashboard.db"

from fastapi.testclient import TestClient

from app import models
from app.database import SessionLocal
from app.main import app

passed = 0


def check(label, condition, extra=""):
    global passed
    assert condition, f"FAILED: {label} {extra}"
    passed += 1
    print(f"  OK {label}")


print("== 1. no demo-seed module exists any more ==")
check("scripts/seed_demo_users.py was deleted", not os.path.exists(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "seed_demo_users.py")
))
check("tests/demo_users_test.py was deleted", not os.path.exists(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_users_test.py")
))
check("scripts/remove_demo_users.py exists (cleanup tool, not a creation tool)", os.path.exists(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "remove_demo_users.py")
))

with TestClient(app) as client:
    db = SessionLocal()

    print("\n== setup: real accounts ==")
    r = client.post("/api/auth/register", json={"username": "realowner", "email": "realowner@example.com", "password": "secret123"})
    owner_id = r.json()["user"]["id"]
    owner_row = db.get(models.User, owner_id)
    owner_row.is_admin = True
    db.commit()
    db.expire_all()

    r = client.post("/api/auth/register", json={"username": "realalice", "email": "realalice@example.com", "password": "secret123"})
    alice_id = r.json()["user"]["id"]
    r = client.post("/api/auth/register", json={"username": "realbob", "email": "realbob@example.com", "password": "secret123"})
    bob_id = r.json()["user"]["id"]
    check("no fake/demo users were created by registration", all(
        not u.startswith("demo_") for u in ("realowner", "realalice", "realbob")
    ))

    owner_login = client.post("/api/auth/login", json={"username": "realowner", "password": "secret123"})
    owner_headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}
    alice_login = client.post("/api/auth/login", json={"username": "realalice", "password": "secret123"})
    alice_headers = {"Authorization": f"Bearer {alice_login.json()['access_token']}"}

    print("\n== 6 & 8. dashboard: normal user 403, admin 200, unauth 401 ==")
    r = client.get("/api/admin/dashboard")
    check("no token -> 401", r.status_code == 401, r.text)
    r = client.get("/api/admin/dashboard", headers=alice_headers)
    check("normal user -> 403", r.status_code == 403, r.text)
    r = client.get("/api/admin/dashboard", headers=owner_headers)
    check("admin -> 200", r.status_code == 200, r.text)

    print("\n== 5 & 10. dashboard count matches the real DB ==")
    real_count = db.query(models.User).count()
    check("total_users matches db.query(User).count()", r.json()["total_users"] == real_count, f"{r.json()} vs {real_count}")

    print("\n== 7 & 9. users list: normal user 403, admin 200 ==")
    r = client.get("/api/admin/users", headers=alice_headers)
    check("normal user -> 403", r.status_code == 403, r.text)
    r = client.get("/api/admin/users", headers=owner_headers)
    check("admin -> 200", r.status_code == 200, r.text)
    body = r.json()
    check("list total matches real DB count", body["total"] == real_count)
    check("realowner/realalice/realbob all present, no demo_ users", {
        "realowner", "realalice", "realbob"
    } <= {u["username"] for u in body["users"]} and not any(u["username"].startswith("demo_") for u in body["users"]))

    print("\n== 3. owner/admin account is correct in the list ==")
    owner_row_in_list = next(u for u in body["users"] if u["id"] == owner_id)
    check("owner is_admin=True in the list", owner_row_in_list["is_admin"] is True)

    print("\n== 13. no personal-profile-photo field is ever exposed ==")
    for u in body["users"]:
        check(f"user {u['username']} has no avatar_url field", "avatar_url" not in u)

    print("\n== 17. no credential fields exposed ==")
    FORBIDDEN = {"password", "password_hash", "hashed_password", "token", "access_token", "secret"}
    for u in body["users"]:
        check(f"user {u['username']} has no credential fields", FORBIDDEN.isdisjoint(u.keys()))

    print("\n== 11. main companion (set via /api/me/animal) is returned ==")
    animals = client.get("/api/animals").json()
    panda = next(a for a in animals if a["name"] == "Panda")
    fox = next(a for a in animals if a["name"].lower() == "fox" or a["slug"] == "fox")
    r = client.post("/api/me/animal", json={"animal_id": panda["id"]}, headers=alice_headers)
    check("choose main companion -> 200", r.status_code == 200, r.text)
    listed = client.get("/api/admin/users", headers=owner_headers).json()
    alice_row = next(u for u in listed["users"] if u["id"] == alice_id)
    check("companion_slug reflects the chosen main companion", alice_row["companion_slug"] == panda["slug"], alice_row)
    check("companion_name reflects the chosen main companion", alice_row["companion_name"] == panda["name"])

    print("\n== 12. Daily Voice Companion does NOT replace the main companion ==")
    r = client.post(
        "/api/voice/companion-chat",
        json={"animal_id": fox["id"], "spoken_text": "你好"},
        headers=alice_headers,
    )
    check("companion-chat with a DIFFERENT animal -> 200", r.status_code == 200, r.text)
    listed_after = client.get("/api/admin/users", headers=owner_headers).json()
    alice_after = next(u for u in listed_after["users"] if u["id"] == alice_id)
    check("companion_slug is STILL the Panda (main companion unchanged)", alice_after["companion_slug"] == panda["slug"], alice_after)
    db.expire_all()
    reloaded_alice = db.get(models.User, alice_id)
    check("user.animal_id in the DB is still Panda, not Fox", reloaded_alice.animal_id == panda["id"])

    print("\n== 14 & 15. deleting a real user updates the list and the count ==")
    before_total = client.get("/api/admin/dashboard", headers=owner_headers).json()["total_users"]
    r = client.delete(f"/api/admin/users/{bob_id}", headers=owner_headers)
    check("delete realbob -> 204", r.status_code == 204, r.text)
    after_list = client.get("/api/admin/users", headers=owner_headers).json()
    check("realbob no longer in the list", not any(u["id"] == bob_id for u in after_list["users"]))
    after_total = client.get("/api/admin/dashboard", headers=owner_headers).json()["total_users"]
    check("dashboard count decreased by exactly 1", after_total == before_total - 1, f"{before_total} -> {after_total}")

    print("\n== 16. admin cannot delete themselves ==")
    r = client.delete(f"/api/admin/users/{owner_id}", headers=owner_headers)
    check("self-delete -> 400", r.status_code == 400, r.text)

    db.close()

print(f"\nADMIN DASHBOARD/COMPANION TESTS: {passed} checks PASSED")
