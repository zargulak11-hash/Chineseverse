"""GitHub sign-in (routers/auth.py /api/auth/github/*, services/github_oauth.py).

A real GitHub authorization needs a person at github.com, so the two calls
that leave this server -- the code exchange and the profile/email read --
are replaced: the router tests stub them at the service boundary, and the
service tests stub httpx itself with a MockTransport. Everything else is
the real flow: /start's state cookie and redirect, the callback's state
check, account resolution and ticket cookie, and the ticket-for-token swap.
"""

from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app import models
from app.config import settings
from app.database import SessionLocal
from app.routers import auth as auth_router
from app.security import create_access_token, create_sign_in_ticket
from app.services import github_oauth
from helpers import bearer, expect, register_raw, unique_name

CALLBACK = "http://testserver/api/auth/github/callback"


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setattr(settings, "github_client_id", "test-github-client")
    monkeypatch.setattr(settings, "github_client_secret", "test-github-secret")
    # http, like a local setup: TestClient talks to http://testserver and
    # would not send back a Secure cookie.
    monkeypatch.setattr(settings, "github_redirect_uri", CALLBACK)


@pytest.fixture(autouse=True)
def fresh_cookies(client):
    client.cookies.clear()
    yield
    client.cookies.clear()


@pytest.fixture
def github_as(monkeypatch):
    """github_as(identity | GitHubAuthError) decides what the next callback's
    code exchange + profile read produce."""
    def set_result(result, expected_code="the-code"):
        def exchange(code):
            assert code == expected_code
            if isinstance(result, github_oauth.GitHubAuthError) and result.code == "github_code":
                raise result
            return "gho_test_access_token"

        def identity(token):
            assert token == "gho_test_access_token"
            if isinstance(result, github_oauth.GitHubAuthError):
                raise result
            return result

        monkeypatch.setattr(github_oauth, "exchange_code", exchange)
        monkeypatch.setattr(github_oauth, "fetch_identity", identity)
    return set_result


def ident(email, gid="1001", name="Git Hubber", login="githubber"):
    return github_oauth.GitHubIdentity(id=gid, email=email, name=name, login=login)


def start(client, page="login"):
    r = client.get("/api/auth/github/start", params={"page": page}, follow_redirects=False)
    assert r.status_code == 302, r.text
    return r


def state_of(start_response):
    return parse_qs(urlparse(start_response.headers["location"]).query)["state"][0]


def callback(client, **params):
    return client.get("/api/auth/github/callback", params=params, follow_redirects=False)


def full_sign_in(client, page="login"):
    """/start -> GitHub (skipped) -> /callback -> /session; returns the
    token response."""
    state = state_of(start(client, page))
    r = callback(client, code="the-code", state=state)
    assert r.status_code == 302 and r.headers["location"] == "/auth/github", (r.status_code, r.headers)
    return expect(client, "post", "/api/auth/github/session", 200)


def users_with_email(email):
    with SessionLocal() as db:
        return db.query(models.User).filter(models.User.email.ilike(email)).count()


# ---------------------------------------------------------------- configuration

def test_providers_reports_what_the_server_can_complete(client, monkeypatch):
    assert expect(client, "get", "/api/auth/providers", 200)["github"] is True
    monkeypatch.setattr(settings, "github_client_secret", None)
    assert expect(client, "get", "/api/auth/providers", 200)["github"] is False


def test_unconfigured_server_sends_the_learner_back_with_a_reason(client, monkeypatch):
    monkeypatch.setattr(settings, "github_client_id", None)
    r = start(client, "register")
    assert r.headers["location"] == "/register?auth_error=github_not_configured"


def test_start_redirects_to_github_with_state_and_no_secret(client):
    r = start(client, "register")
    url = urlparse(r.headers["location"])
    q = parse_qs(url.query)
    assert f"{url.scheme}://{url.netloc}{url.path}" == github_oauth.AUTHORIZE_URL
    assert q["client_id"] == ["test-github-client"] and q["redirect_uri"] == [CALLBACK]
    assert q["scope"] == ["read:user user:email"] and len(q["state"][0]) >= 32
    assert "test-github-secret" not in r.headers["location"]
    cookie = r.headers["set-cookie"]
    assert "cv_github_state=" in cookie and "HttpOnly" in cookie
    assert "Path=/api/auth/github" in cookie and "SameSite=lax" in cookie
    assert r.headers["cache-control"] == "no-store"


def test_cookies_are_secure_when_the_public_callback_is_https(client, monkeypatch):
    monkeypatch.setattr(settings, "github_redirect_uri", None)
    monkeypatch.setattr(settings, "public_app_url", "https://chineseverse.qobus.tj")
    r = start(client)
    assert parse_qs(urlparse(r.headers["location"]).query)["redirect_uri"] == [
        "https://chineseverse.qobus.tj/api/auth/github/callback"
    ]
    assert "Secure" in r.headers["set-cookie"]


def test_an_unknown_return_page_falls_back_to_login(client):
    # Not an open redirect: anything but login/register returns to /login.
    start(client, "https://evil.example.com")
    r = callback(client, error="access_denied", state="whatever")
    assert r.headers["location"] == "/login?auth_error=github_cancelled"


# ---------------------------------------------------------------- state / cancel

def test_state_mismatch_or_missing_cookie_never_signs_in(client, github_as):
    github_as(ident("statecheck@example.com", gid="2001"))
    start(client, "register")
    r = callback(client, code="the-code", state="not-the-state")
    assert r.headers["location"] == "/register?auth_error=github_state"
    client.cookies.clear()
    r = callback(client, code="the-code", state="anything")
    assert r.headers["location"] == "/login?auth_error=github_state"
    assert users_with_email("statecheck@example.com") == 0


def test_cancel_on_github_returns_to_the_page_it_started_from(client):
    start(client, "register")
    r = callback(client, error="access_denied", state="whatever")
    assert r.headers["location"] == "/register?auth_error=github_cancelled"


@pytest.mark.parametrize("code", ["github_code", "github_unreachable", "github_failed", "github_no_email"])
def test_provider_failures_come_back_as_a_reason_and_create_nothing(client, github_as, code):
    github_as(github_oauth.GitHubAuthError(code))
    state = state_of(start(client, "register"))
    r = callback(client, code="the-code", state=state)
    assert r.headers["location"] == f"/register?auth_error={code}"
    assert "cv_github_ticket" not in r.headers.get("set-cookie", "")


# ---------------------------------------------------------------- accounts

def test_new_github_user_gets_a_normal_account_that_starts_in_onboarding(client, github_as, monkeypatch):
    # Even an allowlisted address gets no admin through GitHub.
    monkeypatch.setattr(settings, "admin_emails", ["newgithubber@example.com"])
    github_as(ident("NewGitHubber@example.com", gid="3001", name="New Git Hubber"))
    data = full_sign_in(client, "register")
    user = data["user"]
    assert user["email"] == "NewGitHubber@example.com"
    assert user["onboarding_completed"] is False and user["is_admin"] is False
    me = expect(client, "get", "/api/me", 200, headers=bearer(data["access_token"]))
    assert me["user"]["id"] == user["id"]
    with SessionLocal() as db:
        row = db.get(models.User, user["id"])
        assert row.github_id == "3001" and row.google_sub is None
        assert row.profile is not None and row.streak is not None

    # Signing in again (from Login this time) is the same account.
    assert full_sign_in(client, "login")["user"]["id"] == user["id"]
    assert users_with_email("newgithubber@example.com") == 1


def test_existing_password_account_is_linked_and_keeps_its_onboarding(client, github_as):
    name = unique_name("gitlinked")
    existing = register_raw(client, name)["user"]
    with SessionLocal() as db:
        db.get(models.User, existing["id"]).profile.onboarding_completed = True
        db.commit()
    github_as(ident(f"{name.upper()}@EXAMPLE.COM", gid="4001"))
    user = full_sign_in(client)["user"]
    assert user["id"] == existing["id"] and user["username"] == name
    assert user["onboarding_completed"] is True

    # Linked by id now: a changed GitHub email still finds the account.
    github_as(ident("changed-address@example.com", gid="4001"))
    assert full_sign_in(client)["user"]["id"] == existing["id"]


def test_a_second_github_account_cannot_take_over_a_linked_email(client, github_as):
    github_as(ident("takenover@example.com", gid="5001"))
    full_sign_in(client)
    github_as(ident("takenover@example.com", gid="5002"))
    state = state_of(start(client))
    r = callback(client, code="the-code", state=state)
    assert r.headers["location"] == "/login?auth_error=github_other_account"


def test_deactivated_account_is_refused(client, github_as):
    github_as(ident("deactivated-gh@example.com", gid="6001"))
    uid = full_sign_in(client)["user"]["id"]
    with SessionLocal() as db:
        db.get(models.User, uid).is_active = False
        db.commit()
    state = state_of(start(client))
    assert callback(client, code="the-code", state=state).headers["location"] == "/login?auth_error=deactivated"


# ---------------------------------------------------------------- ticket

def test_the_callback_works_once_and_the_ticket_works_once(client, github_as):
    github_as(ident("onceonly@example.com", gid="7001"))
    state = state_of(start(client))
    assert callback(client, code="the-code", state=state).headers["location"] == "/auth/github"
    # The callback opened a second time: its state cookie is gone.
    assert callback(client, code="the-code", state=state).headers["location"] == "/login?auth_error=github_state"
    expect(client, "post", "/api/auth/github/session", 200)
    # A refreshed /auth/github page: the ticket cookie was cleared.
    r = expect(client, "post", "/api/auth/github/session", 401)
    assert r["detail"] == "This GitHub sign-in has expired. Please try again."


def test_ticket_and_access_token_are_not_interchangeable(client, github_as):
    github_as(ident("tickets@example.com", gid="8001"))
    data = full_sign_in(client)
    uid = data["user"]["id"]
    # A ticket is not a session...
    expect(client, "get", "/api/me", 401, headers=bearer(create_sign_in_ticket(uid)))
    # ...and an access token is not a ticket.
    client.cookies.set(auth_router.TICKET_COOKIE, create_access_token(uid), path=auth_router.GITHUB_COOKIE_PATH)
    expect(client, "post", "/api/auth/github/session", 401)


# ---------------------------------------------------------------- service (httpx stubbed)

def _mock_httpx(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    real_client = httpx.Client
    monkeypatch.setattr(
        github_oauth.httpx, "post",
        lambda url, **kw: real_client(transport=transport).post(url, **kw),
    )
    monkeypatch.setattr(
        github_oauth.httpx, "Client",
        lambda **kw: real_client(transport=transport, **kw),
    )


def test_exchange_sends_the_secret_server_side_and_maps_refusals(monkeypatch):
    seen = {}

    def handler(request):
        seen["body"] = parse_qs(request.content.decode())
        code = seen["body"]["code"][0]
        if code == "good":
            return httpx.Response(200, json={"access_token": "gho_abc", "token_type": "bearer"})
        return httpx.Response(200, json={"error": "bad_verification_code"})

    _mock_httpx(monkeypatch, handler)
    assert github_oauth.exchange_code("good") == "gho_abc"
    assert seen["body"]["client_secret"] == ["test-github-secret"]
    assert seen["body"]["redirect_uri"] == [CALLBACK]
    with pytest.raises(github_oauth.GitHubAuthError) as exc:
        github_oauth.exchange_code("used-twice")
    assert exc.value.code == "github_code"


def test_network_failure_is_unreachable_not_a_500(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("down", request=request)

    _mock_httpx(monkeypatch, handler)
    with pytest.raises(github_oauth.GitHubAuthError) as exc:
        github_oauth.exchange_code("x")
    assert exc.value.code == "github_unreachable"


@pytest.mark.parametrize("emails,expected", [
    ([{"email": "second@example.com", "verified": True, "primary": False},
      {"email": "primary@example.com", "verified": True, "primary": True}], "primary@example.com"),
    # An unverified primary is skipped for a verified secondary.
    ([{"email": "unverified@example.com", "verified": False, "primary": True},
      {"email": "verified@example.com", "verified": True, "primary": False}], "verified@example.com"),
    ([{"email": "only@example.com", "verified": False, "primary": True}], None),
    ([{"email": "1+someone@users.noreply.github.com", "verified": True, "primary": True}], None),
    ([], None),
])
def test_identity_uses_a_verified_real_email_only(monkeypatch, emails, expected):
    def handler(request):
        assert request.headers["authorization"] == "Bearer gho_abc"
        if request.url.path == "/user":
            return httpx.Response(200, json={"id": 9001, "login": "octo", "name": None})
        return httpx.Response(200, json=emails)

    _mock_httpx(monkeypatch, handler)
    if expected is None:
        with pytest.raises(github_oauth.GitHubAuthError) as exc:
            github_oauth.fetch_identity("gho_abc")
        assert exc.value.code == "github_no_email"
    else:
        got = github_oauth.fetch_identity("gho_abc")
        assert (got.id, got.email, got.login) == ("9001", expected, "octo")
