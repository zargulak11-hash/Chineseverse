"""POST /api/me/sessions/revoke: "sign out of all other devices".

Signing out used to only forget the token in one browser, so a token left
on another device stayed valid for its full seven days unless the password
changed. Tokens carry a whole-second `iat` and one from the very second of
the revocation still counts (security.token_predates_password_change), hence
the short sleeps.
"""

import time

from fastapi.security import HTTPAuthorizationCredentials

from app.database import SessionLocal
from app.deps import get_user_or_none
from helpers import bearer, expect, register_raw, unique_name


def login(client, name, password="secret1"):
    return client.post("/api/auth/login", json={"username": name, "password": password})


def test_other_devices_are_signed_out_and_this_one_stays_in(client):
    name = unique_name("everywhere")
    laptop = register_raw(client, name)["access_token"]
    phone = login(client, name).json()["access_token"]
    time.sleep(1.1)

    r = expect(client, "post", "/api/me/sessions/revoke", 200, headers=bearer(laptop))
    fresh = r["access_token"]
    assert r["user"]["username"] == name and fresh not in (laptop, phone)

    assert client.get("/api/me", headers=bearer(phone)).status_code == 401
    assert client.get("/api/me", headers=bearer(laptop)).status_code == 401
    assert client.get("/api/me", headers=bearer(fresh)).status_code == 200
    # Optional-auth routes (lesson bodies, unlocks) stop treating the old
    # token as signed in too: deps.get_user_or_none is what they all use.
    with SessionLocal() as db:
        assert get_user_or_none(HTTPAuthorizationCredentials(scheme="Bearer", credentials=phone), db) is None
        viewer = get_user_or_none(HTTPAuthorizationCredentials(scheme="Bearer", credentials=fresh), db)
        assert viewer is not None and viewer.username == name


def test_the_password_is_unchanged_and_a_new_sign_in_works(client):
    name = unique_name("keepspw")
    token = register_raw(client, name)["access_token"]
    time.sleep(1.1)
    expect(client, "post", "/api/me/sessions/revoke", 200, headers=bearer(token))
    time.sleep(1.1)
    again = login(client, name)
    assert again.status_code == 200
    assert client.get("/api/me", headers=bearer(again.json()["access_token"])).status_code == 200


def test_it_only_ends_the_callers_own_sessions(client):
    mine = register_raw(client, unique_name("mine"))["access_token"]
    theirs = register_raw(client, unique_name("theirs"))["access_token"]
    time.sleep(1.1)
    expect(client, "post", "/api/me/sessions/revoke", 200, headers=bearer(mine))
    assert client.get("/api/me", headers=bearer(theirs)).status_code == 200


def test_it_needs_a_session(client):
    assert client.post("/api/me/sessions/revoke").status_code == 401
