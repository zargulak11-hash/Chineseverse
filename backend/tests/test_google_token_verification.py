"""POST /api/auth/google with REAL signed ID tokens.

test_google_auth.py replaces the whole verify_oauth2_token call, so it
covers the account chain but none of the token checks. Here only Google's
public-certificate download is replaced (by a test key's certificate); the
token itself is a genuine RS256 JWT that google-auth decodes and checks
exactly as in production: signature, issuer, audience and expiry. Then
_verify_google's own checks (verified email, account id) run on the result.

The Android app signs in through Credential Manager with the server's web
client id as serverClientId: its token's `aud` is that web client id and
`azp` is the Android OAuth client. That shape is covered too, so the app's
tokens are known to pass the same unchanged audience check as the website's.
"""

import datetime
import time

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from google.auth import crypt
from google.auth import exceptions as google_exceptions
from google.auth import jwt as google_jwt

from app import models
from app.config import settings
from app.database import SessionLocal
from app.routers import auth as auth_router
from helpers import bearer, expect, register_raw

WEB_CLIENT_ID = "1111-web.apps.googleusercontent.com"
ANDROID_CLIENT_ID = "1111-android.apps.googleusercontent.com"
KEY_ID = "test-key-1"


def _key_and_cert():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-google-certs")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return key_pem, cert.public_bytes(serialization.Encoding.PEM).decode()


@pytest.fixture(scope="module")
def google_key():
    """The "Google" key that signs tokens, and a second key that doesn't
    belong to Google (for forged tokens)."""
    trusted_key, trusted_cert = _key_and_cert()
    forged_key, _ = _key_and_cert()
    return {"key": trusted_key, "cert": trusted_cert, "forged": forged_key}


@pytest.fixture(autouse=True)
def google_certs(monkeypatch, google_key):
    monkeypatch.setattr(settings, "google_client_id", WEB_CLIENT_ID)
    # The one network call in verification: Google's published certificates.
    monkeypatch.setattr(
        auth_router.google_id_token,
        "_fetch_certs",
        lambda request, url: {KEY_ID: google_key["cert"]},
    )


def claims(**overrides):
    now = int(time.time())
    body = {
        "iss": "https://accounts.google.com",
        "aud": WEB_CLIENT_ID,
        "azp": ANDROID_CLIENT_ID,
        "sub": "google-sub-1",
        "email": "token.user@example.com",
        "email_verified": True,
        "name": "Token User",
        "iat": now,
        "exp": now + 3600,
    }
    body.update(overrides)
    return {k: v for k, v in body.items() if v is not None}


def token(google_key, body, *, forged=False):
    signer = crypt.RSASigner.from_string(
        google_key["forged" if forged else "key"], key_id=KEY_ID
    )
    return google_jwt.encode(signer, body).decode()


def sign_in(client, credential, expected):
    return expect(client, "post", "/api/auth/google", expected, json={"credential": credential})


def test_valid_android_token_creates_one_account_and_signs_back_into_it(client, google_key):
    data = sign_in(client, token(google_key, claims()), 200)
    assert data["access_token"]
    assert data["user"]["email"] == "token.user@example.com"
    me = expect(client, "get", "/api/me", 200, headers=bearer(data["access_token"]))
    assert me["user"]["id"] == data["user"]["id"]
    # A second sign-in (a new token) is the same account, never a duplicate.
    again = sign_in(client, token(google_key, claims()), 200)
    assert again["user"]["id"] == data["user"]["id"]


def test_website_token_without_azp_is_accepted_too(client, google_key):
    body = claims(sub="google-sub-web", email="web.user@example.com", azp=WEB_CLIENT_ID)
    assert sign_in(client, token(google_key, body), 200)["user"]["email"] == "web.user@example.com"


# Each case builds its claims when the test RUNS: built at collection, the
# "issued in the future" token stopped being in the future once the suite
# had been running for over an hour, and the case failed.
@pytest.mark.parametrize(
    "case, make_body",
    [
        ("expired", lambda: claims(iat=int(time.time()) - 7200, exp=int(time.time()) - 3600)),
        ("issued in the future", lambda: claims(iat=int(time.time()) + 3600, exp=int(time.time()) + 7200)),
        ("another app's audience", lambda: claims(aud="9999-other.apps.googleusercontent.com")),
        # The Android client id is the token's azp, never its audience:
        # accepting it as one would widen what this server trusts.
        ("android client as audience", lambda: claims(aud=ANDROID_CLIENT_ID)),
        ("not issued by Google", lambda: claims(iss="https://evil.example.com")),
        ("unverified email", lambda: claims(email_verified=False)),
        ("no email", lambda: claims(email=None)),
        ("no account id", lambda: claims(sub=None)),
    ],
)
def test_rejected_tokens_are_a_401_with_a_stable_message(client, google_key, case, make_body):
    r = sign_in(client, token(google_key, make_body()), 401)
    assert r["detail"] in {
        "Google sign-in could not be verified",
        "Google account has no verified email",
        "Google credential has no account id",
    }, (case, r)


def test_token_signed_by_another_key_is_rejected(client, google_key):
    forged = token(google_key, claims(sub="google-sub-forged"), forged=True)
    assert sign_in(client, forged, 401)["detail"] == "Google sign-in could not be verified"


def test_tampered_payload_is_rejected(client, google_key):
    head, _, sig = token(google_key, claims(email="victim@example.com")).split(".")
    swapped_payload = token(google_key, claims(email="attacker@example.com")).split(".")[1]
    sign_in(client, f"{head}.{swapped_payload}.{sig}", 401)


def test_google_unreachable_is_a_503_not_a_401(client, google_key, monkeypatch):
    def unreachable(request, url):
        raise google_exceptions.TransportError("connection reset")

    monkeypatch.setattr(auth_router.google_id_token, "_fetch_certs", unreachable)
    r = sign_in(client, token(google_key, claims()), 503)
    assert r["detail"] == "Could not reach Google to verify the sign-in"


def test_existing_password_account_is_linked_by_verified_email(client, google_key):
    existing = register_raw(client, "token_linked", password="password1")["user"]
    body = claims(sub="google-sub-linked", email="Token_Linked@example.com")
    # Only once the account's own address is proven (the emailed reset link;
    # test_email_linking.py) -- a registration alone never proves it.
    assert sign_in(client, token(google_key, body), 409)["detail"] == auth_router.UNCONFIRMED_EMAIL_DETAIL
    with SessionLocal() as db:
        db.get(models.User, existing["id"]).email_verified_at = datetime.datetime.utcnow()
        db.commit()
    assert sign_in(client, token(google_key, body), 200)["user"]["id"] == existing["id"]
    # Another Google account with the same address can't take the row over.
    intruder = claims(sub="google-sub-intruder", email="token_linked@example.com")
    sign_in(client, token(google_key, intruder), 409)


def test_unverified_email_never_links_an_existing_account(client, google_key):
    register_raw(client, "token_unverified", password="password1")
    body = claims(sub="google-sub-unverified", email="token_unverified@example.com", email_verified=False)
    sign_in(client, token(google_key, body), 401)


def test_providers_tell_the_app_which_client_id_tokens_must_be_for(client, monkeypatch):
    data = expect(client, "get", "/api/auth/providers", 200)
    assert data["google"] is True and data["google_client_id"] == WEB_CLIENT_ID
    monkeypatch.setattr(settings, "google_client_id", None)
    data = expect(client, "get", "/api/auth/providers", 200)
    assert data["google"] is False and data["google_client_id"] is None
