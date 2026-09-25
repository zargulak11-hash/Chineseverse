"""Security tests for the owner-only Admin Users feature (/api/admin/users).

Run against a LIVE backend (default http://127.0.0.1:8001 — an isolated
test database, not the real dev DB) since it needs a real JWT round-trip
through /api/auth/register + /api/auth/login, not just an in-process call.

Covers, in order, the 10 scenarios the feature spec requires:
 1. Unauthenticated request to the admin API is denied.
 2. A normal authenticated user is denied (403), not just redirected.
 3. An authorized admin is allowed.
 4. An authorized admin receives the real user list.
 5. An authorized admin can delete a user.
 6. A normal user cannot delete another user via a direct API call.
 7. (frontend-side; see App.jsx RequireAdmin — not re-tested here in Python)
 8. (frontend-side; see App.jsx RequireAdmin — not re-tested here in Python)
 9. The admin cannot delete their own account via this endpoint.
10. No credential fields (password, password_hash, tokens) ever appear in
    the list response.

Also verifies the admin list response is FK-safe to act on: deletes a user
who both follows/is followed by another user and won a duel, and confirms
no 500/IntegrityError results and the related rows are cleaned up sanely.
"""
import os

import httpx

BASE = os.environ.get("ADMIN_TEST_BASE", "http://127.0.0.1:8001")
c = httpx.Client(base_url=BASE, timeout=10)
passed = 0


def check(label, condition, extra=""):
    global passed
    assert condition, f"FAILED: {label} {extra}"
    passed += 1
    print(f"  OK {label}")


def register(username, email, password="secret123"):
    r = c.post("/api/auth/register", json={"username": username, "email": email, "password": password})
    assert r.status_code == 201, f"register {username} -> {r.status_code}: {r.text}"
    return r.json()


def login(username, password="secret123"):
    r = c.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"login {username} -> {r.status_code}: {r.text}"
    return r.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


print("== setup: register accounts ==")
admin_reg = register("admintestowner", "admintestowner@example.com")
normal_reg = register("normaluser1", "normaluser1@example.com")
victim_reg = register("victimuser1", "victimuser1@example.com")
admin_id, normal_id, victim_id = admin_reg["user"]["id"], normal_reg["user"]["id"], victim_reg["user"]["id"]
check("fresh accounts are not admin by default", admin_reg["user"]["is_admin"] is False)

# Promote admintestowner the same way a real deployment bootstraps its
# first admin: a direct DB write, never a request payload. This mirrors
# alembic/versions/a1c3f9e2d7b4_add_user_is_admin.py's mechanism exactly.
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", os.environ.get("ADMIN_TEST_DATABASE_URL", ""))
from app.database import SessionLocal
from app import models

with SessionLocal() as db:
    row = db.get(models.User, admin_id)
    row.is_admin = True
    db.commit()

admin_login_resp = c.post("/api/auth/login", json={"username": "admintestowner", "password": "secret123"})
check("login as promoted account -> 200", admin_login_resp.status_code == 200)
check("login response reflects is_admin=true", admin_login_resp.json()["user"]["is_admin"] is True)
admin_token = admin_login_resp.json()["access_token"]
normal_token = login("normaluser1")

print("\n== 1. unauthenticated -> denied ==")
r = c.get("/api/admin/users")
check("GET /api/admin/users, no token -> 401", r.status_code == 401, r.text)
r = c.delete(f"/api/admin/users/{victim_id}")
check("DELETE /api/admin/users/{id}, no token -> 401", r.status_code == 401, r.text)

print("\n== 2. authenticated but non-admin -> denied (403, not silently ignored) ==")
r = c.get("/api/admin/users", headers=auth(normal_token))
check("GET as normal user -> 403", r.status_code == 403, r.text)
check("403 body says admin required, doesn't leak data", "detail" in r.json() and "users" not in r.json())

print("\n== 6. normal user cannot delete another user via direct API ==")
r = c.delete(f"/api/admin/users/{victim_id}", headers=auth(normal_token))
check("DELETE as normal user -> 403", r.status_code == 403, r.text)
still_there = c.get(f"/api/users/{victim_id}", headers=auth(admin_token))
check("victim still exists after denied delete attempt", still_there.status_code == 200)

print("\n== 3 & 4. authorized admin -> allowed, real list returned ==")
r = c.get("/api/admin/users", headers=auth(admin_token))
check("GET as admin -> 200", r.status_code == 200, r.text)
body = r.json()
check("response has total + users", "total" in body and "users" in body)
usernames = {u["username"] for u in body["users"]}
check("list contains the real registered accounts", {"admintestowner", "normaluser1", "victimuser1"} <= usernames)
check("total matches list length", body["total"] == len(body["users"]))

print("\n== 10. no credential fields leaked ==")
FORBIDDEN = {"password", "password_hash", "hashed_password", "token", "access_token", "secret"}
for u in body["users"]:
    check(
        f"user {u['username']} has no credential fields",
        FORBIDDEN.isdisjoint(u.keys()),
        f"keys={list(u.keys())}",
    )

print("\n== 9. admin cannot delete their own account via this endpoint ==")
r = c.delete(f"/api/admin/users/{admin_id}", headers=auth(admin_token))
check("DELETE self -> 400, not 204", r.status_code == 400, r.text)
still_admin = c.get("/api/admin/users", headers=auth(admin_token))
check("admin account still present after blocked self-delete", still_admin.status_code == 200)

print("\n== FK-safety: delete a user with a Follow relationship + a Duel win ==")
# victim follows admintestowner, and admintestowner follows victim back —
# exercises both follower_id and following_id pointing at the deleted row.
# Inserted directly via the DB rather than through social.py's follow route,
# so this test doesn't depend on that router's URL shape.
with SessionLocal() as db:
    db.add(models.Follow(follower_id=victim_id, following_id=admin_id))
    db.add(models.Follow(follower_id=admin_id, following_id=victim_id))
    duel = models.Duel(status="finished", winner_id=victim_id)
    db.add(duel)
    db.commit()
    duel_id = duel.id

r = c.delete(f"/api/admin/users/{victim_id}", headers=auth(admin_token))
check("DELETE user with Follow rows + a Duel win -> 204, no 500/IntegrityError", r.status_code == 204, r.text)

with SessionLocal() as db:
    check("Follow rows referencing the deleted user are gone", db.query(models.Follow).filter(
        (models.Follow.follower_id == victim_id) | (models.Follow.following_id == victim_id)
    ).count() == 0)
    reloaded_duel = db.get(models.Duel, duel_id)
    check("Duel record survives with winner_id nulled out", reloaded_duel is not None and reloaded_duel.winner_id is None)

check("deleted user is gone from admin list", victim_id not in {u["id"] for u in c.get("/api/admin/users", headers=auth(admin_token)).json()["users"]})

print("\n== 5. plain admin delete of a normal user works end-to-end ==")
r = c.delete(f"/api/admin/users/{normal_id}", headers=auth(admin_token))
check("DELETE normal user -> 204", r.status_code == 204, r.text)
r = c.get("/api/admin/users", headers=auth(admin_token))
check("deleted user no longer in list", normal_id not in {u["id"] for u in r.json()["users"]})

c.close()
print(f"\nADMIN SECURITY TESTS: {passed} checks PASSED")
