"""Setting a password without the old one: a fresh Google sign-in
(POST /api/auth/google/password) and the emailed "forgot password" link
(POST /api/auth/password/forgot, /reset/check, /reset).

As in test_google_auth.py, only Google's verification call is replaced
(a real Google-signed token needs a real Google sign-in); a garbage
credential still goes through the real verifier. Outgoing email is
captured in memory -- nothing is ever sent.
"""

import hashlib
import re
import time
from datetime import datetime, timedelta

import pytest

from app import models
from app.config import settings
from app.database import SessionLocal
from app.routers import auth as auth_router
from app.services import email as mailer
from app.services import login_throttle, password_reset
from helpers import bearer, expect, register_raw


def login(client, username, password):
    return client.post("/api/auth/login", json={"username": username, "password": password})


# --- set a password with Google ----------------------------------------------


@pytest.fixture
def google_as(monkeypatch):
    """google_as(sub, email, iat=now) makes the next credential verify to
    these claims."""
    monkeypatch.setattr(settings, "google_client_id", "test-client-id.apps.googleusercontent.com")

    def set_claims(sub, email, iat=None):
        claims = {"sub": sub, "email": email, "email_verified": True, "name": "G User",
                  "iat": int(time.time()) if iat is None else iat}
        monkeypatch.setattr(auth_router.google_id_token, "verify_oauth2_token",
                            lambda credential, request, audience: claims)
    return set_claims


def google_account(client, google_as, sub, email):
    google_as(sub, email)
    data = expect(client, "post", "/api/auth/google", 200, json={"credential": "fresh-google-credential"})
    return data["user"], data["access_token"]


def set_with_google(client, token, new="brand-new-pass", confirm=None):
    return client.post(
        "/api/auth/google/password",
        json={"credential": "fresh-google-credential", "new_password": new,
              "confirm_password": new if confirm is None else confirm},
        headers=bearer(token),
    )


def test_google_account_sets_a_password_and_can_then_sign_in_with_it(client, google_as):
    user, token = google_account(client, google_as, "g-sub-1", "gone1@example.com")
    assert user["google_linked"] is True
    # Before: no password the learner knows works.
    assert login(client, user["username"], "brand-new-pass").status_code == 401

    # Tokens carry a whole-second iat, and one from the very second of the
    # change still counts (security.token_predates_password_change).
    time.sleep(1.1)
    r = set_with_google(client, token)
    assert r.status_code == 200, r.text
    fresh = r.json()["access_token"]
    assert login(client, user["username"], "brand-new-pass").status_code == 200
    # Like a password change: older sessions end, the fresh one works.
    assert client.get("/api/me", headers=bearer(token)).status_code == 401
    assert client.get("/api/me", headers=bearer(fresh)).status_code == 200


def test_google_proof_must_be_the_account_bound_to_the_session(client, google_as):
    user, token = google_account(client, google_as, "g-sub-2", "gtwo@example.com")
    # Someone else's Google account (even one claiming the same email).
    google_as("g-sub-intruder", "gtwo@example.com")
    r = set_with_google(client, token)
    assert r.status_code == 403
    assert r.json()["detail"] == "This Google account isn't the one linked to your ChineseVerse account"
    assert login(client, user["username"], "brand-new-pass").status_code == 401


def test_a_session_is_required(client, google_as):
    google_as("g-sub-3", "gthree@example.com")
    r = client.post("/api/auth/google/password", json={
        "credential": "fresh-google-credential", "new_password": "brand-new-pass",
        "confirm_password": "brand-new-pass"})
    assert r.status_code == 401


def test_a_password_account_without_google_is_refused(client, google_as):
    data = register_raw(client, "pwonly1", password="secret1")
    google_as("g-sub-4", "pwonly1@example.com")
    r = set_with_google(client, data["access_token"])
    assert r.status_code == 403
    assert login(client, "pwonly1", "secret1").status_code == 200


def test_a_stale_google_proof_is_refused(client, google_as):
    user, token = google_account(client, google_as, "g-sub-5", "gfive@example.com")
    google_as("g-sub-5", "gfive@example.com", iat=int(time.time()) - 20 * 60)
    r = set_with_google(client, token)
    # 400, not 401: the app signs out on a 401, and the session is fine.
    assert r.status_code == 400
    assert r.json()["detail"] == "Please confirm with Google again"
    assert client.get("/api/me", headers=bearer(token)).status_code == 200


def test_new_password_rules_apply_and_are_never_echoed(client, google_as):
    user, token = google_account(client, google_as, "g-sub-6", "gsix@example.com")
    r = set_with_google(client, token, new="abc")
    assert r.status_code == 422 and "abc" not in r.text
    r = set_with_google(client, token, new="long-enough-1", confirm="long-enough-2")
    assert r.status_code == 422 and r.json()["detail"] == "The new passwords don't match"
    assert login(client, user["username"], "long-enough-1").status_code == 401


def test_a_garbage_credential_is_refused_by_the_real_verifier(client, monkeypatch, google_as):
    user, token = google_account(client, google_as, "g-sub-7", "gseven@example.com")
    monkeypatch.undo()  # the real verifier again
    monkeypatch.setattr(settings, "google_client_id", "test-client-id.apps.googleusercontent.com")
    r = client.post("/api/auth/google/password", json={
        "credential": "not-a-real-google-jwt", "new_password": "brand-new-pass",
        "confirm_password": "brand-new-pass"}, headers=bearer(token))
    assert r.status_code == 400
    assert r.json()["detail"] == "Google sign-in could not be verified"


def test_me_says_whether_google_is_linked_but_never_the_id(client, google_as):
    user, token = google_account(client, google_as, "g-sub-8", "geight@example.com")
    me = expect(client, "get", "/api/me", 200, headers=bearer(token))
    assert me["user"]["google_linked"] is True
    assert "g-sub-8" not in str(me)
    plain = register_raw(client, "pwonly2")
    assert plain["user"]["google_linked"] is False


# --- forgot password by email -------------------------------------------------


@pytest.fixture
def outbox(monkeypatch):
    """SMTP 'configured', every email captured instead of sent."""
    sent = []
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.invalid")
    monkeypatch.setattr(settings, "smtp_from", "ChineseVerse <noreply@test.invalid>")
    monkeypatch.setattr(mailer, "send_email",
                        lambda to, subject, text, html=None: sent.append(
                            {"to": to, "subject": subject, "text": text, "html": html}))
    return sent


def forgot(client, email, **kw):
    return client.post("/api/auth/password/forgot", json={"email": email}, **kw)


def token_from(mail):
    m = re.search(r"/reset-password#token=([A-Za-z0-9_\-]+)", mail["text"])
    assert m, mail["text"]
    return m.group(1)


def reset(client, token, new="reset-pass-1", confirm=None):
    return client.post("/api/auth/password/reset", json={
        "token": token, "new_password": new, "confirm_password": new if confirm is None else confirm})


def test_known_and_unknown_addresses_get_the_same_answer(client, outbox):
    register_raw(client, "fp_known")
    known = forgot(client, "fp_known@example.com")
    unknown = forgot(client, "nobody-here@example.com")
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert [m["to"] for m in outbox] == ["fp_known@example.com"]


def test_the_link_goes_to_the_registered_address_and_only_its_hash_is_stored(client, outbox):
    register_raw(client, "fp_case")
    forgot(client, "FP_CASE@Example.com")
    assert outbox[-1]["to"] == "fp_case@example.com"  # never the typed spelling
    token = token_from(outbox[-1])
    assert "#token=" in outbox[-1]["text"]  # a fragment: never sent to a server
    with SessionLocal() as db:
        row = db.query(models.PasswordResetToken).order_by(models.PasswordResetToken.id.desc()).first()
        assert row.token_hash == hashlib.sha256(token.encode()).hexdigest()
        assert row.token_hash != token


def test_valid_link_resets_signs_in_and_ends_older_sessions(client, outbox):
    old = register_raw(client, "fp_valid", password="old-pass-1")["access_token"]
    forgot(client, "fp_valid@example.com")
    token = token_from(outbox[-1])
    expect(client, "post", "/api/auth/password/reset/check", 200, json={"token": token})
    time.sleep(1.1)
    r = reset(client, token)
    assert r.status_code == 200, r.text
    assert r.json()["user"]["username"] == "fp_valid"
    assert client.get("/api/me", headers=bearer(r.json()["access_token"])).status_code == 200
    assert client.get("/api/me", headers=bearer(old)).status_code == 401
    assert login(client, "fp_valid", "old-pass-1").status_code == 401
    assert login(client, "fp_valid", "reset-pass-1").status_code == 200


def test_a_link_works_once(client, outbox):
    register_raw(client, "fp_reuse")
    forgot(client, "fp_reuse@example.com")
    token = token_from(outbox[-1])
    assert reset(client, token).status_code == 200
    again = reset(client, token, new="another-pass")
    assert again.status_code == 400
    assert again.json()["detail"] == password_reset.INVALID_LINK
    assert login(client, "fp_reuse", "another-pass").status_code == 401
    assert client.post("/api/auth/password/reset/check", json={"token": token}).status_code == 400


def test_an_expired_link_is_refused(client, outbox):
    register_raw(client, "fp_expired", password="kept-pass-1")
    forgot(client, "fp_expired@example.com")
    token = token_from(outbox[-1])
    with SessionLocal() as db:
        row = db.query(models.PasswordResetToken).filter_by(
            token_hash=hashlib.sha256(token.encode()).hexdigest()).one()
        row.expires_at = datetime.utcnow() - timedelta(minutes=1)
        db.commit()
    check = client.post("/api/auth/password/reset/check", json={"token": token})
    assert check.status_code == 400 and check.json()["detail"] == password_reset.EXPIRED_LINK
    r = reset(client, token)
    assert r.status_code == 400 and r.json()["detail"] == password_reset.EXPIRED_LINK
    assert login(client, "fp_expired", "kept-pass-1").status_code == 200


def test_a_made_up_token_is_refused(client, outbox):
    for token in ("", "x", "a" * 120):
        r = reset(client, token)
        assert r.status_code == 400, token
    assert client.post("/api/auth/password/reset", json={
        "token": "a" * 500, "new_password": "whatever1", "confirm_password": "whatever1"}).status_code == 422


def test_asking_again_spends_the_older_link(client, outbox):
    register_raw(client, "fp_twice")
    forgot(client, "fp_twice@example.com")
    first = token_from(outbox[-1])
    forgot(client, "fp_twice@example.com")
    second = token_from(outbox[-1])
    assert reset(client, first).status_code == 400
    assert reset(client, second).status_code == 200


def test_bad_new_password_keeps_the_link_usable(client, outbox):
    register_raw(client, "fp_rules")
    forgot(client, "fp_rules@example.com")
    token = token_from(outbox[-1])
    r = reset(client, token, new="abc")
    assert r.status_code == 422 and "abc" not in r.text
    assert reset(client, token, new="good-pass-1", confirm="good-pass-2").status_code == 422
    assert reset(client, token).status_code == 200


def test_requests_per_account_are_capped_silently(client, outbox):
    register_raw(client, "fp_flood")
    answers = {forgot(client, "fp_flood@example.com").status_code for _ in range(5)}
    assert answers == {202}
    assert len([m for m in outbox if m["to"] == "fp_flood@example.com"]) == password_reset.ACCOUNT_LIMIT_PER_HOUR


def test_requests_per_public_address_are_capped(client, outbox, monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    for i in range(password_reset.IP_LIMIT_PER_HOUR + 2):
        register_raw(client, f"fp_ip{i}")
        assert forgot(client, f"fp_ip{i}@example.com", headers={"X-Forwarded-For": "8.8.8.8"}).status_code == 202
    assert len([m for m in outbox if m["to"].startswith("fp_ip")]) == password_reset.IP_LIMIT_PER_HOUR


def test_a_deactivated_account_gets_no_link(client, outbox):
    register_raw(client, "fp_off")
    with SessionLocal() as db:
        db.query(models.User).filter_by(username="fp_off").one().is_active = False
        db.commit()
    assert forgot(client, "fp_off@example.com").status_code == 202
    assert not [m for m in outbox if m["to"] == "fp_off@example.com"]


def test_a_reset_clears_the_login_lockout(client, outbox):
    register_raw(client, "fp_locked", password="old-pass-1")
    for _ in range(login_throttle.PAIR_LIMIT):
        login(client, "fp_locked", "wrong-guess")
    assert login(client, "fp_locked", "old-pass-1").status_code == 429
    forgot(client, "fp_locked@example.com")
    assert reset(client, token_from(outbox[-1])).status_code == 200
    assert login(client, "fp_locked", "reset-pass-1").status_code == 200


def test_without_email_the_server_says_so_for_every_address(client, monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", None)
    register_raw(client, "fp_nomail")
    known = forgot(client, "fp_nomail@example.com")
    unknown = forgot(client, "nobody-at-all@example.com")
    assert known.status_code == unknown.status_code == 503
    assert known.json() == unknown.json() == {"detail": password_reset.UNAVAILABLE}
    assert expect(client, "get", "/api/auth/providers", 200)["password_reset"] is False


def test_the_email_speaks_the_requesters_language(client, outbox):
    register_raw(client, "fp_ru")
    forgot(client, "fp_ru@example.com", headers={"X-Locale": "ru"})
    assert outbox[-1]["subject"] == "Сброс пароля ChineseVerse"
    assert "fp_ru" in outbox[-1]["text"]
