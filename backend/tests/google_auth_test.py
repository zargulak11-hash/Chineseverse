"""Tests for POST /api/auth/google.

A real Google-signed ID token can't be generated in a test (it requires an
actual Google sign-in), so the token *verification call itself* is
monkeypatched to return controlled claims — this is the standard way to
test an OIDC integration without hitting the live identity provider. The
"invalid token" case is NOT mocked: it calls the real verifier with a
garbage string, so that failure path is genuinely exercised end to end.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/google_auth.db"

from fastapi.testclient import TestClient  # noqa: E402

from app import config  # noqa: E402
from app.main import app  # noqa: E402
from app.routers import auth as auth_router  # noqa: E402


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, (
        f"{method.upper()} {url} -> {resp.status_code} (expected {expected}): {resp.text}"
    )
    return resp


def fake_verifier(claims):
    """Return a stand-in for google.oauth2.id_token.verify_oauth2_token."""
    def _verify(credential, request, audience):
        if credential == "__raise_malformed__":
            raise ValueError("Token used too early")
        return claims
    return _verify


with TestClient(app) as client:
    # --- Unconfigured server: 501, not a crash -----------------------------
    original_client_id = config.settings.google_client_id
    config.settings.google_client_id = None
    expect(
        client, "post", "/api/auth/google", 501,
        json={"credential": "irrelevant-but-long-enough"},
    )
    print("[PASS] unconfigured server returns 501, not a 500")
    config.settings.google_client_id = original_client_id or "test-client-id.apps.googleusercontent.com"

    # --- Genuinely invalid token: real verifier call, no mocking -----------
    r = client.post("/api/auth/google", json={"credential": "not-a-real-jwt-at-all"})
    assert r.status_code == 401, r.text
    print("[PASS] garbage credential rejected with 401 (real verification path)")

    # --- New user is created from valid claims ------------------------------
    original_verify = auth_router.google_id_token.verify_oauth2_token
    auth_router.google_id_token.verify_oauth2_token = fake_verifier({
        "email": "newgoogleuser@example.com",
        "email_verified": True,
        "name": "New Google User",
        "sub": "1234567890",
    })
    try:
        r = expect(client, "post", "/api/auth/google", 200, json={"credential": "fake-but-long-enough"})
        data = r.json()
        assert data["user"]["email"] == "newgoogleuser@example.com"
        assert data["user"]["username"].startswith("new_google_user") or data["user"]["username"].startswith("newgoogleuser")
        assert data["access_token"]
        new_user_id = data["user"]["id"]
        print(f"[PASS] new user created from Google claims: username={data['user']['username']!r}")

        # Calling again with the same email must log into the SAME account,
        # not create a duplicate.
        r2 = expect(client, "post", "/api/auth/google", 200, json={"credential": "fake-but-long-enough"})
        assert r2.json()["user"]["id"] == new_user_id
        print("[PASS] second Google login with same email reuses the same account")

        # --- Unverified email is rejected ------------------------------------
        auth_router.google_id_token.verify_oauth2_token = fake_verifier({
            "email": "unverified@example.com",
            "email_verified": False,
        })
        expect(client, "post", "/api/auth/google", 401, json={"credential": "fake-but-long-enough"})
        print("[PASS] unverified email is rejected with 401")

        # --- Existing email/password account is reused, not duplicated ------
        reg = client.post("/api/auth/register", json={
            "username": "priorpassworduser",
            "email": "shared@example.com",
            "password": "password1",
        })
        assert reg.status_code == 201, reg.text
        existing_user_id = reg.json()["user"]["id"]

        auth_router.google_id_token.verify_oauth2_token = fake_verifier({
            "email": "shared@example.com",
            "email_verified": True,
            "name": "Shared Account",
        })
        r3 = expect(client, "post", "/api/auth/google", 200, json={"credential": "fake-but-long-enough"})
        assert r3.json()["user"]["id"] == existing_user_id
        assert r3.json()["user"]["username"] == "priorpassworduser"
        print("[PASS] Google login for an email already registered by password logs into that same account")

        # --- Username collision gets a numeric suffix, not a 500 -------------
        auth_router.google_id_token.verify_oauth2_token = fake_verifier({
            "email": "collision1@example.com",
            "email_verified": True,
            "name": "Collide Name",
        })
        u1 = expect(client, "post", "/api/auth/google", 200, json={"credential": "fake-but-long-enough"}).json()["user"]
        auth_router.google_id_token.verify_oauth2_token = fake_verifier({
            "email": "collision2@example.com",
            "email_verified": True,
            "name": "Collide Name",
        })
        u2 = expect(client, "post", "/api/auth/google", 200, json={"credential": "fake-but-long-enough"}).json()["user"]
        assert u1["username"] != u2["username"], (u1, u2)
        print(f"[PASS] username collision resolved: {u1['username']!r} vs {u2['username']!r}")
    finally:
        auth_router.google_id_token.verify_oauth2_token = original_verify

print("ALL GOOGLE AUTH TESTS PASSED")
