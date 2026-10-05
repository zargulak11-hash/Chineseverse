"""POST /api/auth/google: the identity chain (Google sub -> verified email
-> new account) and the admin allowlist.

A real Google-signed ID token can't be generated in a test (it requires an
actual Google sign-in), so the token *verification call itself* is
monkeypatched to return controlled claims -- the standard way to test an
OIDC integration without hitting the live identity provider. The "invalid
token" case is NOT mocked: it calls the real verifier with a garbage
string, so that failure path is genuinely exercised end to end.
"""

import pytest

from app.config import settings
from app.routers import auth as auth_router
from helpers import bearer, expect, register_raw

CREDENTIAL = {"credential": "fake-but-long-enough"}


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "test-client-id.apps.googleusercontent.com")


@pytest.fixture
def google_as(monkeypatch):
    """google_as(claims) makes the next sign-ins verify to these claims."""
    def set_claims(claims):
        def verify(credential, request, audience):
            assert audience == settings.google_client_id
            return claims
        monkeypatch.setattr(auth_router.google_id_token, "verify_oauth2_token", verify)
    return set_claims


def sign_in(client, expected=200):
    return expect(client, "post", "/api/auth/google", expected, json=CREDENTIAL)


def test_unconfigured_server_answers_501_not_500(client, monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", None)
    expect(client, "post", "/api/auth/google", 501, json={"credential": "irrelevant-but-long-enough"})


def test_garbage_credential_is_rejected_by_the_real_verifier(client):
    r = client.post("/api/auth/google", json={"credential": "not-a-real-jwt-at-all"})
    assert r.status_code == 401, r.text
    # The verifier's own wording stays in the server log; the learner gets a
    # stable sentence the frontend maps to a translated message.
    assert r.json()["detail"] == "Google sign-in could not be verified"


def test_new_account_from_claims_and_the_same_account_next_time(client, google_as):
    google_as({"email": "newgoogleuser@example.com", "email_verified": True,
               "name": "New Google User", "sub": "1234567890"})
    data = sign_in(client)
    assert data["user"]["email"] == "newgoogleuser@example.com"
    assert data["user"]["username"].startswith(("new_google_user", "newgoogleuser"))
    assert data["access_token"]
    assert data["user"]["is_admin"] is False
    # Signing in again must log into the SAME account, not create a duplicate.
    assert sign_in(client)["user"]["id"] == data["user"]["id"]


@pytest.mark.parametrize("claims", [
    {"email": "unverified@example.com", "email_verified": False, "sub": "sub-unverified"},
    {"email": "nosub@example.com", "email_verified": True},
    {"sub": "sub-noemail", "email_verified": True},
])
def test_unverified_email_or_missing_identity_is_rejected(client, google_as, claims):
    google_as(claims)
    sign_in(client, 401)


def test_existing_password_account_is_linked_not_duplicated(client, google_as):
    existing = register_raw(client, "priorpassworduser", password="password1")["user"]
    # Same address, different letter case: still the same person.
    google_as({"email": "PriorPasswordUser@Example.com", "email_verified": True,
               "name": "Shared Account", "sub": "sub-shared"})
    linked = sign_in(client)["user"]
    assert linked["id"] == existing["id"] and linked["username"] == "priorpassworduser"
    assert linked["is_admin"] is False

    # Once linked, the Google sub wins even if the Google email changes.
    google_as({"email": "renamed@example.com", "email_verified": True, "sub": "sub-shared"})
    assert sign_in(client)["user"]["id"] == existing["id"]

    # A different Google account can't take over the already-linked row.
    google_as({"email": "priorpassworduser@example.com", "email_verified": True, "sub": "sub-intruder"})
    sign_in(client, 409)


def test_admin_only_via_google_verified_allowlisted_email(client, google_as, monkeypatch):
    monkeypatch.setattr(settings, "admin_emails", ["owner@example.com"])
    reg_owner = client.post("/api/auth/register", json={
        "username": "OwnerByPassword", "email": "owner@example.com", "password": "password1",
    })
    # A password registration never proves email ownership -> no admin.
    assert reg_owner.status_code == 201 and reg_owner.json()["user"]["is_admin"] is False

    google_as({"email": "owner@example.com", "email_verified": True, "sub": "sub-owner"})
    r = sign_in(client)
    assert r["user"]["id"] == reg_owner.json()["user"]["id"] and r["user"]["is_admin"] is True, r
    me = expect(client, "get", "/api/me", 200, headers=bearer(r["access_token"]))
    assert me["user"]["is_admin"] is True


def test_registration_rejects_case_insensitive_duplicates(client):
    register_raw(client, "CaseOwner", password="password1")
    dup = client.post("/api/auth/register", json={
        "username": "caseowner", "email": "x@example.com", "password": "password1",
    })
    assert dup.status_code == 409, dup.text
    dup = client.post("/api/auth/register", json={
        "username": "someoneelse", "email": "CASEOWNER@example.com", "password": "password1",
    })
    assert dup.status_code == 409, dup.text


def test_username_collision_gets_a_suffix_not_a_500(client, google_as):
    google_as({"email": "collision1@example.com", "email_verified": True, "sub": "sub-c1", "name": "Collide Name"})
    u1 = sign_in(client)["user"]
    google_as({"email": "collision2@example.com", "email_verified": True, "sub": "sub-c2", "name": "Collide Name"})
    u2 = sign_in(client)["user"]
    assert u1["username"] != u2["username"], (u1, u2)
