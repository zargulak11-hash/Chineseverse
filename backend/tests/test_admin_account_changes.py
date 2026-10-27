"""What an admin's edit of a user (PUT/PATCH /api/users/{id}) does to that
user's reset links and sessions.

- Moving an account to another email spends every reset link already sent:
  each went to the OLD address, and used later it would reset the account
  and mark the new, never-proven address as verified -- a way around the
  rule that Google/GitHub only join an account whose email was proven
  (test_email_linking.py).
- Setting a password ends every session opened before it, as the learner's
  own password change does; it used to only swap the hash.

Tokens carry a whole-second `iat`, hence the short sleeps.
"""

import re
import time

import pytest

from app import models
from app.config import settings
from app.database import SessionLocal
from app.services import email as mailer
from helpers import bearer, expect, register_raw, unique_name


@pytest.fixture
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.invalid")
    monkeypatch.setattr(settings, "smtp_from", "ChineseVerse <noreply@test.invalid>")
    monkeypatch.setattr(mailer, "send_email",
                        lambda to, subject, text, html=None: sent.append({"to": to, "text": text}))
    return sent


@pytest.fixture(scope="module")
def admin(client):
    data = register_raw(client, unique_name("useradmin"))
    with SessionLocal() as db:
        db.get(models.User, data["user"]["id"]).is_admin = True
        db.commit()
    return bearer(data["access_token"])


def login(client, name, password):
    return client.post("/api/auth/login", json={"username": name, "password": password})


def reset_link(client, outbox, email):
    expect(client, "post", "/api/auth/password/forgot", 202, json={"email": email})
    assert outbox and outbox[-1]["to"] == email
    return re.search(r"#token=([A-Za-z0-9_\-]+)", outbox[-1]["text"]).group(1)


def use_link(client, token, new="link-pass-1"):
    return client.post("/api/auth/password/reset",
                       json={"token": token, "new_password": new, "confirm_password": new})


def verified(user_id):
    with SessionLocal() as db:
        return db.get(models.User, user_id).email_verified_at is not None


def full_update(name, email, password):
    return {"username": name, "email": email, "password": password, "animal_id": None}


# ------------------------------------------------------ email change vs links


@pytest.mark.parametrize("method", ["patch", "put"])
def test_a_link_sent_before_an_email_change_stops_working(client, outbox, admin, method):
    name = unique_name("moved")
    user = register_raw(client, name, password="before-pass-1")["user"]
    token = reset_link(client, outbox, f"{name}@example.com")
    expect(client, "post", "/api/auth/password/reset/check", 200, json={"token": token})

    new_email = f"{unique_name('newaddr')}@example.com"
    body = {"email": new_email} if method == "patch" else full_update(name, new_email, "before-pass-1")
    expect(client, method, f"/api/users/{user['id']}", 200, json=body, headers=admin)

    r = client.post("/api/auth/password/reset/check", json={"token": token})
    assert r.status_code == 400 and r.json()["detail"] == "This reset link is invalid or was already used"
    assert use_link(client, token).status_code == 400
    # Neither reset nor proven by the stale link.
    assert verified(user["id"]) is False
    assert login(client, name, "before-pass-1").status_code == 200
    assert login(client, name, "link-pass-1").status_code == 401


def test_the_normal_flow_works_for_the_new_address(client, outbox, admin):
    name = unique_name("newflow")
    user = register_raw(client, name)["user"]
    reset_link(client, outbox, f"{name}@example.com")
    new_email = f"{unique_name('fresh')}@example.com"
    expect(client, "patch", f"/api/users/{user['id']}", 200, json={"email": new_email}, headers=admin)

    # A link asked for now goes to the new address and works as before.
    token = reset_link(client, outbox, new_email)
    r = use_link(client, token, new="new-addr-pass")
    assert r.status_code == 200 and r.json()["user"]["id"] == user["id"]
    assert verified(user["id"]) is True
    assert login(client, name, "new-addr-pass").status_code == 200


@pytest.mark.parametrize("body", [
    lambda name: {"username": f"{name}_renamed"},
    # The same address in another letter case is not a move.
    lambda name: {"email": f"{name.upper()}@EXAMPLE.COM"},
], ids=["rename only", "same address, other case"])
def test_edits_that_keep_the_address_leave_open_links_alone(client, outbox, admin, body):
    name = unique_name("keeps")
    user = register_raw(client, name)["user"]
    token = reset_link(client, outbox, f"{name}@example.com")
    expect(client, "patch", f"/api/users/{user['id']}", 200, json=body(name), headers=admin)
    expect(client, "post", "/api/auth/password/reset/check", 200, json={"token": token})
    assert use_link(client, token).status_code == 200


# ----------------------------------------------- admin-set password vs sessions


@pytest.mark.parametrize("method", ["patch", "put"])
def test_an_admin_set_password_ends_the_users_sessions(client, admin, method):
    name = unique_name("adminpw")
    first = register_raw(client, name, password="old-pass-1")
    second = login(client, name, "old-pass-1").json()["access_token"]
    bystander = register_raw(client, unique_name("bystander"))["access_token"]
    time.sleep(1.1)

    uid = first["user"]["id"]
    body = ({"password": "admin-set-pass"} if method == "patch"
            else full_update(name, f"{name}@example.com", "admin-set-pass"))
    expect(client, method, f"/api/users/{uid}", 200, json=body, headers=admin)

    for old in (first["access_token"], second):
        assert client.get("/api/me", headers=bearer(old)).status_code == 401
    assert login(client, name, "old-pass-1").status_code == 401
    again = login(client, name, "admin-set-pass")
    assert again.status_code == 200
    assert client.get("/api/me", headers=bearer(again.json()["access_token"])).status_code == 200
    # Nobody else is signed out -- including the admin who made the change.
    assert client.get("/api/me", headers=bearer(bystander)).status_code == 200
    assert client.get("/api/me", headers=admin).status_code == 200


@pytest.mark.parametrize("field", ["email", "username"])
def test_an_explicit_null_for_a_required_column_is_a_422_not_a_500(client, admin, field):
    # Both columns are NOT NULL: a null used to reach the database and fail
    # there (IntegrityError -> 500). Leaving the field out still means "keep it".
    name = unique_name("nullpatch")
    user = register_raw(client, name)["user"]
    r = client.patch(f"/api/users/{user['id']}", json={field: None}, headers=admin)
    assert r.status_code == 422, r.text
    with SessionLocal() as db:
        row = db.get(models.User, user["id"])
        assert row.username == name and row.email == f"{name}@example.com"
    # Other nullable fields still accept null, and an absent field is untouched.
    expect(client, "patch", f"/api/users/{user['id']}", 200, json={"animal_id": None}, headers=admin)


def test_a_patch_without_a_password_keeps_the_users_sessions(client, admin):
    data = register_raw(client, unique_name("nopw"))
    time.sleep(1.1)
    expect(client, "patch", f"/api/users/{data['user']['id']}", 200,
           json={"username": unique_name("renamed")}, headers=admin)
    assert client.get("/api/me", headers=bearer(data["access_token"])).status_code == 200
