"""The real-users-only Admin Users/Home system: GET /api/admin/dashboard,
GET /api/admin/users (companion, auth method, activity, paging, search,
database source) and DELETE /api/admin/users/{id} -- all admin-only, none
exposing credentials or profile photos, and no demo-user seed path."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from app import models
from app.config import settings
from app.database import SessionLocal
from app.routers import auth as auth_router
from helpers import bearer, expect

BACKEND = Path(__file__).resolve().parent.parent
FORBIDDEN = {"password", "password_hash", "hashed_password", "token", "access_token", "secret"}


def make_account(client, name):
    r = expect(client, "post", "/api/auth/register", 201,
               json={"username": name, "email": f"{name}@example.com", "password": "secret123"})
    return r["user"]["id"]


def login(client, name):
    return bearer(expect(client, "post", "/api/auth/login", 200,
                         json={"username": name, "password": "secret123"})["access_token"])


@pytest.fixture(scope="module")
def accounts(client):
    owner_id = make_account(client, "realowner")
    with SessionLocal() as db:
        db.get(models.User, owner_id).is_admin = True
        db.commit()
    alice_id = make_account(client, "realalice")
    return SimpleNamespace(
        owner_id=owner_id, owner=login(client, "realowner"),
        alice_id=alice_id, alice=login(client, "realalice"),
    )


def users(client, headers, query=""):
    return expect(client, "get", f"/api/admin/users{query}", 200, headers=headers)


def test_no_demo_user_seed_path_exists():
    assert not (BACKEND / "scripts" / "seed_demo_users.py").exists()
    assert not (BACKEND / "tests" / "demo_users_test.py").exists()
    # The cleanup tool stays (it removes demo users, never creates them).
    assert (BACKEND / "scripts" / "remove_demo_users.py").exists()


def test_admin_routes_are_admin_only(client, accounts):
    for path in ("/api/admin/dashboard", "/api/admin/users"):
        expect(client, "get", path, 401)
        expect(client, "get", path, 403, headers=accounts.alice)
        expect(client, "get", path, 200, headers=accounts.owner)
    # Paging parameters don't open a way around the check.
    expect(client, "get", "/api/admin/users?limit=1&q=a", 403, headers=accounts.alice)
    expect(client, "delete", f"/api/admin/users/{accounts.owner_id}", 403, headers=accounts.alice)


def test_counts_and_list_are_the_real_user_table(client, accounts):
    with SessionLocal() as db:
        real_count = db.query(models.User).count()
    assert expect(client, "get", "/api/admin/dashboard", 200, headers=accounts.owner)["total_users"] == real_count
    body = users(client, accounts.owner)
    assert body["total"] == real_count
    names = {u["username"] for u in body["users"]}
    assert {"realowner", "realalice"} <= names and not any(n.startswith("demo_") for n in names)
    assert next(u for u in body["users"] if u["id"] == accounts.owner_id)["is_admin"] is True


def test_list_exposes_no_credentials_or_profile_photo(client, accounts):
    for u in users(client, accounts.owner)["users"]:
        assert "avatar_url" not in u
        assert FORBIDDEN.isdisjoint(u.keys()), u


def test_main_companion_is_listed_and_the_daily_voice_companion_never_replaces_it(client, accounts):
    animals = client.get("/api/animals").json()
    panda = next(a for a in animals if a["name"] == "Panda")
    fox = next(a for a in animals if a["slug"] == "fox")
    expect(client, "post", "/api/me/animal", 200, json={"animal_id": panda["id"]}, headers=accounts.alice)
    row = next(u for u in users(client, accounts.owner)["users"] if u["id"] == accounts.alice_id)
    assert row["companion_slug"] == panda["slug"] and row["companion_name"] == panda["name"], row

    expect(client, "post", "/api/voice/companion-chat", 200,
           json={"animal_id": fox["id"], "spoken_text": "你好"}, headers=accounts.alice)
    row = next(u for u in users(client, accounts.owner)["users"] if u["id"] == accounts.alice_id)
    assert row["companion_slug"] == panda["slug"], row
    with SessionLocal() as db:
        assert db.get(models.User, accounts.alice_id).animal_id == panda["id"]


def test_deleting_a_user_updates_list_and_count_but_not_oneself(client, accounts):
    bob_id = make_account(client, "realbob")
    before = expect(client, "get", "/api/admin/dashboard", 200, headers=accounts.owner)["total_users"]
    expect(client, "delete", f"/api/admin/users/{bob_id}", 204, headers=accounts.owner)
    assert not any(u["id"] == bob_id for u in users(client, accounts.owner)["users"])
    after = expect(client, "get", "/api/admin/dashboard", 200, headers=accounts.owner)["total_users"]
    assert after == before - 1
    expect(client, "delete", f"/api/admin/users/{accounts.owner_id}", 400, headers=accounts.owner)


def test_auth_method_google_id_and_last_activity(client, accounts, monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(auth_router.google_id_token, "verify_oauth2_token", lambda *a, **k: {
        "email": "realalice@example.com", "email_verified": True, "sub": "google-sub-alice",
    })
    expect(client, "post", "/api/auth/google", 200, json={"credential": "fake-but-long-enough"})

    s = expect(client, "post", "/api/practice/sessions", 201,
               json={"source": "vocab", "hsk_level": 1, "size": 4}, headers=accounts.alice)
    with SessionLocal() as db:
        q0 = db.get(models.PracticeSession, s["id"]).questions[0]
    expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200,
           json={"index": 0, "choice_id": q0["item_id"]}, headers=accounts.alice)

    body = users(client, accounts.owner)
    rows = {u["id"]: u for u in body["users"]}
    alice, owner = rows[accounts.alice_id], rows[accounts.owner_id]
    assert alice["auth_method"] == "google" and alice["google_sub"] == "google-sub-alice", alice
    assert owner["auth_method"] == "password" and owner["google_sub"] is None
    with SessionLocal() as db:
        newest = (db.query(models.ActivityEvent.created_at).filter_by(user_id=accounts.alice_id)
                  .order_by(models.ActivityEvent.created_at.desc()).first()[0])
        real_total = db.query(models.User).count()
        real_admins = db.query(models.User).filter(models.User.is_admin.is_(True)).count()
    assert alice["last_activity_at"].startswith(newest.isoformat()[:19]), alice
    assert owner["last_activity_at"] is None
    assert (body["total_users"], body["admin_count"], body["regular_count"]) == (
        real_total, real_admins, real_total - real_admins), body


def test_paging_and_case_insensitive_search(client, accounts):
    with SessionLocal() as db:
        ordered = [u.id for u in db.query(models.User).order_by(models.User.id)]
    page = users(client, accounts.owner, "?limit=1&offset=1")
    assert [u["id"] for u in page["users"]] == ordered[1:2] and page["total"] == len(ordered), page
    found = users(client, accounts.owner, "?q=REALALICE")
    assert [u["id"] for u in found["users"]] == [accounts.alice_id] and found["total"] == 1, found
    expect(client, "get", "/api/admin/users?limit=0", 422, headers=accounts.owner)


def test_database_source_is_described_without_credentials(client, accounts):
    dbinfo = users(client, accounts.owner)["database"]
    assert dbinfo["engine"] == "sqlite" and dbinfo["name"] == "test_admin_dashboard.db", dbinfo
    assert dbinfo["environment"] == "test", dbinfo
    assert not any("@" in str(v) or "password" in str(v).lower() for v in dbinfo.values())
    local = users(client, {**accounts.owner, "Host": "localhost:8000"})["database"]
    prod = users(client, {**accounts.owner, "Host": "chineseverse.qobus.tj"})["database"]
    assert local["environment"] == "local", local
    assert prod["environment"] == "production" and prod["served_by"] == "chineseverse.qobus.tj", prod


def test_a_promoted_admin_signs_in_as_admin_and_a_403_leaks_nothing(client, accounts):
    # Fresh accounts are never admin; the promotion (a DB write, as in a real
    # deployment) is what the login response then reports.
    r = expect(client, "post", "/api/auth/login", 200, json={"username": "realowner", "password": "secret123"})
    assert r["user"]["is_admin"] is True
    assert expect(client, "post", "/api/auth/login", 200,
                  json={"username": "realalice", "password": "secret123"})["user"]["is_admin"] is False
    body = expect(client, "get", "/api/admin/users", 403, headers=accounts.alice)
    assert "detail" in body and "users" not in body
    victim_id = make_account(client, "victimuser1")
    expect(client, "delete", f"/api/admin/users/{victim_id}", 403, headers=accounts.alice)
    expect(client, "get", f"/api/users/{victim_id}", 200, headers=accounts.owner)  # still there


def test_deleting_a_user_with_follows_a_duel_win_placement_and_activity_is_fk_safe(client, accounts):
    # PlacementAttempt and ActivityEvent were a real gap: neither has a
    # cascade on User, and freshly created test accounts never have them, so
    # it only surfaced on real accounts. See crud.delete_user_cascade_safe.
    victim_id = make_account(client, "fkvictim")
    owner_id = accounts.owner_id
    with SessionLocal() as db:
        db.add(models.Follow(follower_id=victim_id, following_id=owner_id))
        db.add(models.Follow(follower_id=owner_id, following_id=victim_id))
        duel = models.Duel(status="completed", winner_id=victim_id)
        db.add(duel)
        db.add(models.PlacementAttempt(user_id=victim_id, status="finished", placed_level=2))
        db.add(models.ActivityEvent(user_id=victim_id, section="hanzi", action_type="review", minutes=1.0))
        db.commit()
        duel_id = duel.id
    expect(client, "delete", f"/api/admin/users/{victim_id}", 204, headers=accounts.owner)
    with SessionLocal() as db:
        assert db.query(models.Follow).filter(
            (models.Follow.follower_id == victim_id) | (models.Follow.following_id == victim_id)).count() == 0
        reloaded = db.get(models.Duel, duel_id)
        assert reloaded is not None and reloaded.winner_id is None  # the duel record survives
        assert db.query(models.PlacementAttempt).filter_by(user_id=victim_id).count() == 0
        assert db.query(models.ActivityEvent).filter_by(user_id=victim_id).count() == 0
    assert victim_id not in {u["id"] for u in users(client, accounts.owner)["users"]}
