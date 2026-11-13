"""POST /api/auth/google: the identity chain (Google sub -> verified email
-> new account) and the admin allowlist.

A real Google-signed ID token can't be generated in a test (it requires an
actual Google sign-in), so the token *verification call itself* is
monkeypatched to return controlled claims -- the standard way to test an
OIDC integration without hitting the live identity provider.

The verifier's own checks (signature, audience, expiry, issuer) are NOT
mocked: the real google-auth verifier runs against tokens signed with a
test key, and only the download of Google's signing certificates is
served locally (`google_certs`). That download is the one network call
in the chain; it used to make the "garbage credential" test fail with a
503 whenever Google's cert endpoint was slow from the test machine. The
live call is still exercised by test_garbage_credential_against_live_google.
"""

import json
import time
import types
from datetime import datetime, timedelta

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from google.auth import crypt as google_crypt
from google.auth import exceptions as google_exceptions
from google.auth import jwt as google_jwt

from app import models
from app.config import settings
from app.database import SessionLocal
from app.routers import auth as auth_router
from helpers import bearer, expect, register_raw

CREDENTIAL = {"credential": "fake-but-long-enough"}


def confirm_email(user_id):
    """What the emailed reset link does to a password account's address
    (exercised end to end in test_email_linking.py)."""
    with SessionLocal() as db:
        db.get(models.User, user_id).email_verified_at = datetime.utcnow()
        db.commit()


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


def _key_and_cert(name):
    """An RSA key and a self-signed certificate for it, in the PEM form
    Google publishes its signing certificates in."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = datetime.utcnow()
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=1))
            .sign(key, hashes.SHA256()))
    pem_key = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption())
    return pem_key, cert.public_bytes(serialization.Encoding.PEM).decode()


GOOGLE_KEY, GOOGLE_CERT = _key_and_cert("test google signing key")
OTHER_KEY, _ = _key_and_cert("someone else's key")
KID = "test-kid"
CERTS_URL = "https://www.googleapis.com/oauth2/v1/certs"


def signed_token(key=GOOGLE_KEY, **overrides):
    now = int(time.time())
    claims = {"iss": "https://accounts.google.com", "aud": "test-client-id.apps.googleusercontent.com",
              "sub": "sub-real-verifier", "email": "realverifier@example.com", "email_verified": True,
              "name": "Real Verifier", "iat": now, "exp": now + 3600, **overrides}
    signer = google_crypt.RSASigner.from_string(key, key_id=KID)
    return google_jwt.encode(signer, claims).decode()


@pytest.fixture
def google_certs(monkeypatch):
    """Serve Google's certificate download locally; everything else in
    the real verifier runs. Returns the list of URLs fetched, and
    google_certs.fail() makes the download fail like a network error."""
    class Fetched(list):
        def fail(self):
            state["fail"] = True

    fetched = Fetched()
    state = {"fail": False}

    class Response:
        status = 200
        headers = {"content-type": "application/json"}
        data = json.dumps({KID: GOOGLE_CERT}).encode()

    class Request:
        def __call__(self, url, method="GET", body=None, headers=None, timeout=None, **kwargs):
            fetched.append(url)
            if state["fail"]:
                raise google_exceptions.TransportError("timed out reaching Google")
            return Response()

    monkeypatch.setattr(auth_router, "google_requests", types.SimpleNamespace(Request=Request))
    return fetched


def google_post(client, credential, expected):
    return expect(client, "post", "/api/auth/google", expected, json={"credential": credential})


def test_garbage_credential_is_rejected_by_the_real_verifier(client, google_certs):
    r = google_post(client, "not-a-real-jwt-at-all", 401)
    # The verifier's own wording stays in the server log; the learner gets a
    # stable sentence the frontend maps to a translated message.
    assert r["detail"] == "Google sign-in could not be verified"
    assert google_certs == [CERTS_URL], "the real verifier must have run"


def test_a_token_signed_by_google_signs_in_through_the_real_verifier(client, google_certs):
    data = google_post(client, signed_token(), 200)
    assert data["user"]["email"] == "realverifier@example.com" and data["access_token"]
    assert data["user"]["is_admin"] is False


@pytest.mark.parametrize("credential", [
    pytest.param(lambda: signed_token(aud="someone-elses-client.apps.googleusercontent.com"), id="wrong-audience"),
    pytest.param(lambda: signed_token(iat=int(time.time()) - 7200, exp=int(time.time()) - 3600), id="expired"),
    # A correctly signed token from another issuer raises a bare
    # GoogleAuthError, not a ValueError (the branch that once became a 503).
    pytest.param(lambda: signed_token(iss="https://evil.example.com"), id="wrong-issuer"),
    pytest.param(lambda: signed_token(key=OTHER_KEY), id="not-signed-by-google"),
])
def test_the_real_verifier_rejects_bad_tokens_with_401(client, google_certs, credential):
    assert google_post(client, credential(), 401)["detail"] == "Google sign-in could not be verified"


def test_unreachable_google_is_503_not_401(client, google_certs):
    google_certs.fail()
    r = google_post(client, signed_token(), 503)
    assert r["detail"] == "Could not reach Google to verify the sign-in"


def test_garbage_credential_against_live_google(client):
    """The one test that really talks to Google. When Google's cert
    endpoint can't be reached from this machine the server rightly answers
    503; that is an outage, not a bug (test_unreachable_google_is_503_not_401
    covers the handling), so the test is skipped with the reason shown
    instead of failing."""
    r = client.post("/api/auth/google", json={"credential": "not-a-real-jwt-at-all"})
    if r.status_code == 503 and r.json()["detail"] == "Could not reach Google to verify the sign-in":
        pytest.skip("Google's certificate endpoint was unreachable from this machine")
    assert r.status_code == 401, r.text
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


def test_existing_password_account_is_linked_once_its_email_is_confirmed(client, google_as):
    existing = register_raw(client, "priorpassworduser", password="password1")["user"]
    # Same address, different letter case: still the same person.
    google_as({"email": "PriorPasswordUser@Example.com", "email_verified": True,
               "name": "Shared Account", "sub": "sub-shared"})
    # The registration never proved the address, so not yet.
    assert sign_in(client, 409)["detail"] == auth_router.UNCONFIRMED_EMAIL_DETAIL
    confirm_email(existing["id"])
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
    # Nor does Google join it -- and so grant admin -- before the account's
    # own address is proven.
    sign_in(client, 409)
    me = expect(client, "get", "/api/me", 200, headers=bearer(reg_owner.json()["access_token"]))
    assert me["user"]["is_admin"] is False
    confirm_email(reg_owner.json()["user"]["id"])
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
