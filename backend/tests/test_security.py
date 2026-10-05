"""Token handling and account state at the edges: malformed, expired,
foreign-signed and unsigned tokens are a 401 (never a 500), a deactivated
account loses every privilege its unexpired token carried, and an avatar
upload must really be the image type it claims to be."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app import models
from app.config import settings
from app.database import SessionLocal
from app.security import create_access_token
from app.services import avatars
from helpers import bearer, expect, register, unique_name

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360f8cfc0f01f0005000201e2b1f7a40000000049454e44ae426082"
)


def signed(payload, secret=None, algorithm="HS256"):
    return jwt.encode(payload, secret or settings.jwt_secret, algorithm=algorithm)


@pytest.fixture
def learner(client):
    return register(client, unique_name("sec"))


def test_a_valid_token_works(client, learner):
    uid, _ = learner
    expect(client, "get", "/api/me", 200, headers=bearer(create_access_token(uid)))


@pytest.mark.parametrize("make", [
    lambda uid: signed({"iat": datetime.now(timezone.utc)}),  # no subject
    lambda uid: signed({"sub": "not-a-number"}),
    lambda uid: signed({"sub": str(uid), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}),
    lambda uid: signed({"sub": str(uid)}, secret="someone-elses-secret"),
    lambda uid: jwt.encode({"sub": str(uid)}, key=None, algorithm="none"),
    lambda uid: "not.a.jwt",
], ids=["no-sub", "non-numeric-sub", "expired", "foreign-secret", "alg-none", "garbage"])
def test_a_bad_token_is_a_401_never_a_500(client, learner, make):
    uid, _ = learner
    r = client.get("/api/me", headers=bearer(make(uid)))
    assert r.status_code == 401, (r.status_code, r.text)


def test_a_token_for_a_deleted_account_is_a_401(client):
    assert client.get("/api/me", headers=bearer(create_access_token(999_999))).status_code == 401


def test_a_deactivated_admins_token_loses_every_privilege(client):
    uid, h = register(client, unique_name("former_admin"))
    with SessionLocal() as db:
        db.get(models.User, uid).is_admin = True
        db.commit()
    assert any(l["content"] for l in expect(client, "get", "/api/lessons", 200, headers=h))
    with SessionLocal() as db:
        db.get(models.User, uid).is_active = False
        db.commit()
    # Optional-auth routes treat the token as anonymous...
    assert all(l["content"] is None for l in expect(client, "get", "/api/lessons", 200, headers=h))
    # ...and every protected route refuses it.
    expect(client, "get", "/api/me", 401, headers=h)
    expect(client, "get", "/api/admin/users", 401, headers=h)


@pytest.mark.parametrize("name, mime, data", [
    ("fake.png", "image/png", b"<svg onload=alert(1)>"),
    ("fake.jpg", "image/jpeg", b"\x89PNG\r\n\x1a\n" + b"0" * 32),
    ("fake.webp", "image/webp", b"RIFF0000WAVEfmt "),
], ids=["html-as-png", "png-bytes-as-jpeg", "riff-but-not-webp"])
def test_an_avatar_whose_bytes_are_not_the_declared_image_is_refused(client, learner, name, mime, data):
    uid, h = learner
    r = client.post("/api/me/avatar", headers=h, files={"file": (name, data, mime)})
    assert r.status_code == 415, r.text
    assert r.json()["detail"] == "Only JPG, PNG or WEBP images are allowed"
    with SessionLocal() as db:
        assert db.query(models.UserProfile).filter_by(user_id=uid).one().avatar_url is None
    assert not list(avatars.AVATAR_DIR.glob(f"user{uid}_*"))


def test_a_real_png_avatar_is_still_accepted(client, learner):
    _, h = learner
    url = expect(client, "post", "/api/me/avatar", 200, headers=h, files={"file": ("a.png", PNG, "image/png")})["avatar_url"]
    assert avatars.file_for(url).is_file()
    expect(client, "delete", "/api/me/avatar", 200, headers=h)
