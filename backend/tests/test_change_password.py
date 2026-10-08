"""POST /api/me/password: only the signed-in learner, only with the right
current password, the registration password rule, nothing echoed back; the
new password signs in, the old one doesn't, and every session opened
before the change ends while the one that made it carries on."""

from datetime import datetime, timedelta, timezone

import jwt

from app import models
from app.config import settings
from app.database import SessionLocal
from helpers import bearer, expect, expect_response, register_raw, unique_name

URL = "/api/me/password"


def learner(client, password="secret1"):
    name = unique_name("pw")
    data = register_raw(client, name, password)
    return name, bearer(data["access_token"])


def change(client, h, current, new, confirm=None, expected=200):
    return expect(client, "post", URL, expected, headers=h, json={
        "current_password": current, "new_password": new,
        "confirm_password": new if confirm is None else confirm,
    })


def session_opened_earlier(user_id, seconds_ago=30):
    """A real access token, as one issued `seconds_ago` would be (tokens
    carry whole-second issue times, so "earlier" must be a past second)."""
    now = datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)
    token = jwt.encode({"sub": str(user_id), "iat": now, "exp": now + timedelta(days=7)},
                       settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return bearer(token)


def can_login(client, name, password):
    return client.post("/api/auth/login", json={"username": name, "password": password}).status_code == 200


def test_changing_the_password_signs_in_with_the_new_one_only(client):
    name, h = learner(client)
    body = change(client, h, "secret1", "brand-new-pass")
    assert body["user"]["username"] == name and body["access_token"]
    assert can_login(client, name, "brand-new-pass")
    assert not can_login(client, name, "secret1")
    with SessionLocal() as db:
        u = db.query(models.User).filter_by(username=name).one()
        assert u.password_hash.startswith("pbkdf2_sha256$") and "brand-new-pass" not in u.password_hash
        assert u.password_changed_at is not None


def test_the_changing_session_carries_on_and_older_sessions_end(client):
    name, _ = learner(client)
    with SessionLocal() as db:
        uid = db.query(models.User).filter_by(username=name).one().id
    this_device, other_device = session_opened_earlier(uid, 60), session_opened_earlier(uid, 5)
    expect(client, "get", "/api/me", 200, headers=other_device)  # valid before the change
    body = change(client, this_device, "secret1", "brand-new-pass")
    fresh = bearer(body["access_token"])
    # The token handed back works at once (same second as the change).
    assert expect(client, "get", "/api/me", 200, headers=fresh)["user"]["username"] == name
    for stale in (this_device, other_device):
        assert expect(client, "get", "/api/me", 401, headers=stale)["detail"] == "Invalid or expired token"
    # ... and a stale token is anonymous on optional-auth routes too.
    assert client.get("/api/animals", headers=other_device).status_code == 200


def test_a_wrong_current_password_changes_nothing_and_keeps_the_session(client):
    name, h = learner(client)
    body = change(client, h, "not-my-password", "brand-new-pass", expected=400)
    assert body["detail"] == "Current password is incorrect"
    assert can_login(client, name, "secret1") and not can_login(client, name, "brand-new-pass")
    expect(client, "get", "/api/me", 200, headers=h)  # 400, not 401: still signed in


def test_the_new_password_must_be_confirmed_valid_and_new(client):
    name, h = learner(client)
    cases = [
        (("secret1", "brand-new-pass", "brand-new-typo"), "The new passwords don't match"),
        (("secret1", "short", None), "The new password must be at least 6 characters"),
        (("secret1", "", None), "The new password must be at least 6 characters"),
        (("secret1", "x" * 129, None), "The new password must be at most 128 characters"),
        (("secret1", "secret1", None), "The new password must be different from the current one"),
        (("", "brand-new-pass", None), "Enter your current password"),
    ]
    for (current, new, confirm), detail in cases:
        assert change(client, h, current, new, confirm, expected=422)["detail"] == detail
    assert can_login(client, name, "secret1")


def test_nothing_secret_comes_back(client):
    _, h = learner(client)
    for current, new, confirm, status in (
        ("secret1", "brand-new-pass", None, 200),
        ("wrong-guess-123", "another-pass-1", None, 400),
        ("brand-new-pass", "x" * 200, None, 422),
    ):
        resp = expect_response(client, "post", URL, status, headers=h, json={
            "current_password": current, "new_password": new, "confirm_password": confirm or new})
        assert current not in resp.text and new not in resp.text and "pbkdf2" not in resp.text
        if status == 200:
            h = bearer(resp.json()["access_token"])


def test_guessing_the_current_password_is_throttled_like_sign_in(client):
    name, h = learner(client)
    codes = [client.post(URL, headers=h, json={"current_password": f"guess-{i}", "new_password": "brand-new-pass",
                                                "confirm_password": "brand-new-pass"}).status_code
             for i in range(25)]
    assert codes[0] == 400 and 429 in codes, codes
    # Locked: even the right password is refused until the lock runs out.
    change(client, h, "secret1", "brand-new-pass", expected=429)


def test_changing_the_password_requires_sign_in(client):
    body = {"current_password": "secret1", "new_password": "brand-new-pass", "confirm_password": "brand-new-pass"}
    expect(client, "post", URL, 401, json=body)
    expect(client, "post", URL, 401, json=body, headers=bearer("not-a-token"))
