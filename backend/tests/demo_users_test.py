"""Tests for scripts/seed_demo_users.py and its interaction with the
Admin Users API. Runs in-process (FastAPI TestClient) against a fresh
temp sqlite database, same convention as smoke_test.py, since the demo
seed script talks to the DB directly rather than through the API.

Covers the 9 required scenarios:
 1. seed creates the demo users
 2. running seed twice does not duplicate them
 3. demo users have is_admin = False
 4. an existing owner/admin account is left unchanged by the seed
 5. admin can see demo users via GET /api/admin/users
 6. admin can delete one demo user
 7. normal user cannot access GET /api/admin/users
 8. normal user cannot DELETE /api/admin/users/{id}
 9. no password/hash fields are ever returned by the admin list
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/demo_users.db"

from fastapi.testclient import TestClient

from app import models
from app.database import SessionLocal
from app.main import app
from scripts.seed_demo_users import DEMO_USERS, seed_demo_users

passed = 0


def check(label, condition, extra=""):
    global passed
    assert condition, f"FAILED: {label} {extra}"
    passed += 1
    print(f"  OK {label}")


with TestClient(app) as client:
    db = SessionLocal()

    # A pre-existing owner/admin account, promoted the same way the real
    # migration does — direct DB write, never a request payload.
    r = client.post("/api/auth/register", json={"username": "realowner", "email": "realowner@example.com", "password": "secret123"})
    assert r.status_code == 201, r.text
    owner_id = r.json()["user"]["id"]
    owner_row = db.get(models.User, owner_id)
    owner_row.is_admin = True
    db.commit()
    db.expire_all()

    print("== 1. seed creates the demo users ==")
    created, skipped = seed_demo_users(db)
    check("6 demo users created", len(created) == 6 and set(created) == {u for u, _ in DEMO_USERS})
    check("nothing skipped on first run", skipped == [])

    print("\n== 2. running seed twice does not duplicate ==")
    created2, skipped2 = seed_demo_users(db)
    check("second run creates none", created2 == [])
    check("second run skips all 6", set(skipped2) == {u for u, _ in DEMO_USERS})
    total_demo_rows = db.query(models.User).filter(models.User.username.in_([u for u, _ in DEMO_USERS])).count()
    check("exactly 6 demo rows exist in the DB (no duplicates)", total_demo_rows == 6)

    print("\n== 3. demo users have is_admin = False ==")
    for username, email in DEMO_USERS:
        row = db.query(models.User).filter_by(username=username).first()
        check(f"{username}.is_admin is False", row.is_admin is False)
        check(f"{username}.email matches the fixed demo domain", row.email == email)

    print("\n== 4. existing owner/admin account is unchanged ==")
    db.expire_all()
    reloaded_owner = db.get(models.User, owner_id)
    check("owner is still admin", reloaded_owner.is_admin is True)
    check("owner's username untouched", reloaded_owner.username == "realowner")
    check("owner's email untouched", reloaded_owner.email == "realowner@example.com")

    db.close()

    owner_login = client.post("/api/auth/login", json={"username": "realowner", "password": "secret123"})
    owner_headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}

    r = client.post("/api/auth/register", json={"username": "plainuser", "email": "plainuser@example.com", "password": "secret123"})
    plain_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    print("\n== 5. admin can see demo users via the real API ==")
    r = client.get("/api/admin/users", headers=owner_headers)
    check("GET /api/admin/users -> 200", r.status_code == 200, r.text)
    body = r.json()
    listed_demo_usernames = {u["username"] for u in body["users"] if u["username"].startswith("demo_")}
    check("all 6 demo users appear in the list", listed_demo_usernames == {u for u, _ in DEMO_USERS})

    print("\n== 9. no password/hash fields are ever returned ==")
    FORBIDDEN = {"password", "password_hash", "hashed_password", "token", "access_token", "secret"}
    for u in body["users"]:
        check(f"user {u['username']} has no credential fields", FORBIDDEN.isdisjoint(u.keys()))

    print("\n== 7 & 8. normal user cannot access or delete via admin API ==")
    r = client.get("/api/admin/users", headers=plain_headers)
    check("GET as normal user -> 403", r.status_code == 403, r.text)
    demo_alice_id = next(u["id"] for u in body["users"] if u["username"] == "demo_alice")
    r = client.delete(f"/api/admin/users/{demo_alice_id}", headers=plain_headers)
    check("DELETE as normal user -> 403", r.status_code == 403, r.text)
    still_there = client.get("/api/admin/users", headers=owner_headers)
    check("demo_alice still present after denied delete", any(u["username"] == "demo_alice" for u in still_there.json()["users"]))

    print("\n== 6. admin can delete one demo user ==")
    r = client.delete(f"/api/admin/users/{demo_alice_id}", headers=owner_headers)
    check("DELETE demo_alice as admin -> 204", r.status_code == 204, r.text)
    after = client.get("/api/admin/users", headers=owner_headers).json()
    remaining_demo = {u["username"] for u in after["users"] if u["username"].startswith("demo_")}
    check("demo_alice is gone", "demo_alice" not in remaining_demo)
    check("the other 5 demo users are still present", remaining_demo == {u for u, _ in DEMO_USERS} - {"demo_alice"})

print(f"\nDEMO USERS TESTS: {passed} checks PASSED")
