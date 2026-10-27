"""Google/GitHub sign-in joins an existing account by email only when that
account's own email was proven (routers/auth.py _link_by_email).

The hole this closes ("pre-account takeover"): a password registration
never proves the address is the registrant's, yet a later Google or GitHub
sign-in with that address used to land in the same account -- so someone
could register a victim's email with a password of their own, wait for the
victim's first Google sign-in, and keep signing in with the password. With
an address in ADMIN_EMAILS that was admin.

The provider calls are replaced as in test_google_auth.py and
test_github_auth.py (a real sign-in needs a real person at Google/GitHub);
outgoing email is captured as in test_password_recovery.py. The migration's
backfill is tested in test_email_verified_migration.py.
"""

import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy.exc import IntegrityError

from app import models
from app.config import settings
from app.database import SessionLocal
from app.routers import auth as auth_router
from app.services import email as mailer
from app.services import github_oauth
from helpers import bearer, expect, register_raw, unique_name

UNCONFIRMED = auth_router.UNCONFIRMED_EMAIL_DETAIL
CALLBACK = "http://testserver/api/auth/github/callback"
FRONTEND_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "github_client_id", "test-github-client")
    monkeypatch.setattr(settings, "github_client_secret", "test-github-secret")
    monkeypatch.setattr(settings, "github_redirect_uri", CALLBACK)


@pytest.fixture
def google_as(monkeypatch):
    """google_as(sub, email) makes the next Google credential verify to a
    Google-verified identity with this account id and address."""
    def set_claims(sub, email):
        claims = {"sub": sub, "email": email, "email_verified": True, "name": "Google Person",
                  "iat": int(time.time())}
        monkeypatch.setattr(auth_router.google_id_token, "verify_oauth2_token",
                            lambda credential, request, audience: claims)
    return set_claims


@pytest.fixture
def github_as(monkeypatch):
    """github_as(gid, email): the next GitHub callback yields this identity."""
    def set_identity(gid, email):
        identity = github_oauth.GitHubIdentity(id=gid, email=email, name="Git Person", login="gitperson")
        monkeypatch.setattr(github_oauth, "exchange_code", lambda code: "gho_test_access_token")
        monkeypatch.setattr(github_oauth, "fetch_identity", lambda token: identity)
    return set_identity


@pytest.fixture
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.invalid")
    monkeypatch.setattr(settings, "smtp_from", "ChineseVerse <noreply@test.invalid>")
    monkeypatch.setattr(mailer, "send_email",
                        lambda to, subject, text, html=None: sent.append({"to": to, "text": text}))
    return sent


def google_sign_in(client, expected):
    return expect(client, "post", "/api/auth/google", expected, json={"credential": "fresh-google-credential"})


def github_callback(client, page="login"):
    """/start -> /callback; returns the callback's redirect target."""
    client.cookies.clear()  # no flow cookie left over from an earlier test
    r = client.get("/api/auth/github/start", params={"page": page}, follow_redirects=False)
    state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
    r = client.get("/api/auth/github/callback", params={"code": "the-code", "state": state},
                   follow_redirects=False)
    assert r.status_code == 302, r.text
    return r


def login(client, username, password):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def confirm_email_by_reset(client, outbox, email, new_password="owner-pass-1"):
    """The real owner's way in: the emailed reset link (sent to the
    account's address), used. Returns the token response."""
    expect(client, "post", "/api/auth/password/forgot", 202, json={"email": email})
    token = re.search(r"#token=([A-Za-z0-9_\-]+)", outbox[-1]["text"]).group(1)
    return expect(client, "post", "/api/auth/password/reset", 200, json={
        "token": token, "new_password": new_password, "confirm_password": new_password})


def row(user_id):
    with SessionLocal() as db:
        u = db.get(models.User, user_id)
        return {"google_sub": u.google_sub, "github_id": u.github_id, "is_admin": u.is_admin,
                "verified": u.email_verified_at is not None, "password_hash": u.password_hash}


def accounts_with(email):
    with SessionLocal() as db:
        return db.query(models.User).filter(models.User.email.ilike(email)).count()


# --------------------------------------------------------------- the attack


def test_google_never_joins_an_account_whose_email_was_never_proven(client, google_as):
    name = unique_name("squatter")
    squat = register_raw(client, name, password="squatter-pass")
    victim_email = f"{name}@example.com"
    before = row(squat["user"]["id"])
    assert before["verified"] is False

    # The victim's first Google sign-in, in another letter case too.
    for spelling in (victim_email, victim_email.upper()):
        google_as("victim-google-sub", spelling)
        r = google_sign_in(client, 409)
        assert r["detail"] == UNCONFIRMED

    after = row(squat["user"]["id"])
    assert after["google_sub"] is None and after["password_hash"] == before["password_hash"]
    assert accounts_with(victim_email) == 1  # no second account either


def test_github_never_joins_an_account_whose_email_was_never_proven(client, github_as):
    name = unique_name("ghsquatter")
    squat = register_raw(client, name, password="squatter-pass")
    github_as("9101", f"{name.upper()}@EXAMPLE.COM")
    r = github_callback(client, "login")
    assert r.headers["location"] == "/login?auth_error=github_email_unconfirmed"
    assert "cv_github_ticket" not in r.headers.get("set-cookie", "")
    expect(client, "post", "/api/auth/github/session", 401)
    assert row(squat["user"]["id"])["github_id"] is None


def test_a_lost_sign_in_race_is_held_to_the_same_rule(client, google_as, monkeypatch):
    # Two requests for one sign-in: this one saw "no user yet", lost the
    # insert, and falls back to a lookup by email -- which must not hand it
    # an unproven account.
    name = unique_name("raced")
    squat = register_raw(client, name)["user"]
    real_find = auth_router._find_by_email
    calls = {"n": 0}

    def find(db, email):
        calls["n"] += 1
        return None if calls["n"] == 1 else real_find(db, email)

    def lost_insert(*args, **kwargs):
        raise IntegrityError("INSERT INTO users", {}, Exception("duplicate email"))

    monkeypatch.setattr(auth_router, "_find_by_email", find)
    monkeypatch.setattr(auth_router, "_create_user_from_email", lost_insert)
    google_as("race-google-sub", f"{name}@example.com")
    assert google_sign_in(client, 409)["detail"] == UNCONFIRMED
    assert row(squat["id"])["google_sub"] is None


# --------------------------------------------------------- legitimate use


def test_the_owner_confirms_by_reset_link_then_google_links(client, google_as, outbox):
    name = unique_name("owner")
    email = f"{name}@example.com"
    # Whoever registered it (the owner who forgot, or a squatter) ...
    first = register_raw(client, name, password="first-pass-1")
    google_as("owner-google-sub", email)
    google_sign_in(client, 409)

    # ... the inbox's owner takes it back: the old password and every older
    # session end, and the address now counts as proven.
    time.sleep(1.1)  # tokens carry whole-second iat
    reset = confirm_email_by_reset(client, outbox, email)
    assert reset["user"]["id"] == first["user"]["id"]
    assert login(client, name, "first-pass-1").status_code == 401
    assert client.get("/api/me", headers=bearer(first["access_token"])).status_code == 401
    assert row(first["user"]["id"])["verified"] is True

    linked = google_sign_in(client, 200)["user"]
    assert linked["id"] == first["user"]["id"] and linked["google_linked"] is True
    # From now on by Google's account id, and the password still works.
    google_as("owner-google-sub", "renamed-at-google@example.com")
    assert google_sign_in(client, 200)["user"]["id"] == first["user"]["id"]
    assert login(client, name, "owner-pass-1").status_code == 200
    # Another Google account with the same address still can't take it.
    google_as("someone-elses-sub", email)
    assert google_sign_in(client, 409)["detail"] == "This email is linked to a different Google account"


def test_github_links_once_the_email_is_confirmed(client, github_as, outbox):
    name = unique_name("ghowner")
    first = register_raw(client, name)["user"]
    confirm_email_by_reset(client, outbox, f"{name}@example.com")
    github_as("9202", f"{name}@example.com")
    assert github_callback(client).headers["location"] == "/auth/github"
    assert expect(client, "post", "/api/auth/github/session", 200)["user"]["id"] == first["id"]
    assert row(first["id"])["github_id"] == "9202"


def test_a_provider_created_account_is_joined_by_the_other_provider(client, google_as, github_as):
    # Google verified the address when it created the account, so GitHub
    # with the same verified address is the same person.
    email = f"{unique_name('both')}@example.com"
    google_as("both-google-sub", email)
    created = google_sign_in(client, 200)["user"]
    assert row(created["id"])["verified"] is True
    github_as("9303", email)
    assert github_callback(client).headers["location"] == "/auth/github"
    assert expect(client, "post", "/api/auth/github/session", 200)["user"]["id"] == created["id"]


def test_a_refused_link_changes_nothing_for_the_password_account(client, google_as):
    name = unique_name("pwkeeper")
    data = register_raw(client, name, password="keep-this-1")
    google_as("other-google-sub", f"{name}@example.com")
    google_sign_in(client, 409)
    # Same session, same password, same account.
    me = expect(client, "get", "/api/me", 200, headers=bearer(data["access_token"]))
    assert me["user"]["id"] == data["user"]["id"] and me["user"]["google_linked"] is False
    assert login(client, name, "keep-this-1").status_code == 200


# ------------------------------------------------------------------ admin


def test_an_allowlisted_address_registered_by_password_never_becomes_admin(client, google_as, outbox, monkeypatch):
    name = unique_name("adminsquat")
    email = f"{name}@example.com"
    monkeypatch.setattr(settings, "admin_emails", [email])
    squat = register_raw(client, name, password="squatter-pass")
    assert squat["user"]["is_admin"] is False

    google_as("real-admin-sub", email)
    assert google_sign_in(client, 409)["detail"] == UNCONFIRMED
    assert row(squat["user"]["id"])["is_admin"] is False
    headers = bearer(squat["access_token"])
    assert expect(client, "get", "/api/me", 200, headers=headers)["user"]["is_admin"] is False
    expect(client, "get", "/api/admin/users", 403, headers=headers)
    # The squatter's own password login is still an ordinary learner.
    assert login(client, name, "squatter-pass").json()["user"]["is_admin"] is False

    # The address's real owner proves it, and only then is admin granted.
    time.sleep(1.1)
    confirm_email_by_reset(client, outbox, email)
    assert login(client, name, "squatter-pass").status_code == 401
    assert client.get("/api/me", headers=headers).status_code == 401
    admin = google_sign_in(client, 200)
    assert admin["user"]["id"] == squat["user"]["id"] and admin["user"]["is_admin"] is True


def test_an_address_an_admin_types_in_is_not_proven(client, google_as, outbox):
    # An admin moving an account to a new address doesn't prove the owner
    # controls it: Google with that address must not join the account.
    moved_name = unique_name("moved")
    moved = register_raw(client, moved_name)["user"]
    confirm_email_by_reset(client, outbox, f"{moved_name}@example.com", new_password="moved-pass-1")
    assert row(moved["id"])["verified"] is True
    admin_name = unique_name("emailadmin")
    admin = register_raw(client, admin_name)
    with SessionLocal() as db:
        db.get(models.User, admin["user"]["id"]).is_admin = True
        db.commit()
    new_email = f"{unique_name('typed')}@example.com"
    expect(client, "patch", f"/api/users/{moved['id']}", 200, json={"email": new_email},
           headers=bearer(admin["access_token"]))
    assert row(moved["id"])["verified"] is False
    google_as("typed-address-google-sub", new_email)
    assert google_sign_in(client, 409)["detail"] == UNCONFIRMED
    assert row(moved["id"])["google_sub"] is None
    # The owner's password is untouched by the move.
    assert login(client, moved_name, "moved-pass-1").status_code == 200


def test_the_refusal_is_a_sentence_the_app_translates():
    # The app shows `detail` through frontend/src/apiErrors.js, which maps
    # exact sentences to translations; rewording one side alone would show
    # this guidance in English to every learner (apiErrors.test.js checks
    # the four translations exist).
    api_errors = (FRONTEND_SRC / "apiErrors.js").read_text(encoding="utf-8")
    assert f"'{UNCONFIRMED}': \"emailUnconfirmed\"" in api_errors
    social_auth = (FRONTEND_SRC / "components" / "SocialAuth.jsx").read_text(encoding="utf-8")
    assert '"github_email_unconfirmed"' in social_auth
