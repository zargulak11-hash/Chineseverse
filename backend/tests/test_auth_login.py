"""Password login and its brute-force protection (services/login_throttle).

Everything goes through the real POST /api/auth/login; only the throttle's
clock is replaced so a 15-minute lock can be crossed without sleeping."""

import pytest
from starlette.requests import Request

from app import models
from app.config import settings
from app.database import SessionLocal
from app.deps import get_client_ip
from app.routers import auth as auth_router
from app.security import hash_password, verify_password
from app.services import login_throttle
from helpers import bearer, expect, register_raw

INVALID = "Invalid username or password"


class Clock:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(login_throttle, "_now", c)
    return c


@pytest.fixture
def behind_proxy(monkeypatch):
    """One trusted proxy: the client is the last X-Forwarded-For entry."""
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)


def login(client, username, password, ip=None):
    headers = {"X-Forwarded-For": ip} if ip else {}
    return client.post(
        "/api/auth/login", json={"username": username, "password": password}, headers=headers
    )


def fail_times(client, username, n, ip=None):
    for _ in range(n):
        r = login(client, username, "wrong-password", ip)
        assert r.status_code == 401, r.text


@pytest.fixture(scope="module")
def accounts(client):
    for name in ("alice", "bob", "carol", "dave"):
        register_raw(client, name, password="correct-horse")
    return "correct-horse"


# --- normal behaviour -------------------------------------------------------


def test_successful_login_returns_a_working_token(client, accounts):
    r = login(client, "alice", accounts)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["username"] == "alice"
    assert "password_hash" not in body["user"]
    me = expect(client, "get", "/api/me", 200, headers=bearer(body["access_token"]))
    assert me["user"]["username"] == "alice"


def test_wrong_password_and_unknown_user_get_the_same_answer(client, accounts):
    wrong = login(client, "alice", "nope-nope")
    unknown = login(client, "no_such_learner", "nope-nope")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": INVALID}


def test_passwords_are_stored_hashed_and_compared_in_constant_time(client, accounts):
    with SessionLocal() as db:
        stored = db.query(models.User).filter_by(username="alice").one().password_hash
    assert "correct-horse" not in stored
    assert stored.startswith("pbkdf2_sha256$")
    assert verify_password("correct-horse", stored)
    assert not verify_password("correct-horsf", stored)
    assert not verify_password("x", "garbage-without-separators")
    # Same password, different salt -> different hash.
    assert hash_password("same") != hash_password("same")


def test_unknown_username_still_costs_a_password_check(client, monkeypatch):
    calls = []
    monkeypatch.setattr(auth_router, "burn_password_check", lambda pw: calls.append(pw))
    assert login(client, "ghost_user", "whatever").status_code == 401
    assert calls == ["whatever"]


def test_deactivated_account_with_right_password_is_refused(client, accounts):
    with SessionLocal() as db:
        db.query(models.User).filter_by(username="dave").one().is_active = False
        db.commit()
    try:
        r = login(client, "dave", accounts)
        assert r.status_code == 403
        assert r.json()["detail"] == "This account has been deactivated"
    finally:
        with SessionLocal() as db:
            db.query(models.User).filter_by(username="dave").one().is_active = True
            db.commit()


# --- throttling -------------------------------------------------------------


def test_repeated_failures_lock_the_account_even_for_the_right_password(client, accounts, clock):
    fail_times(client, "alice", login_throttle.PAIR_LIMIT)
    r = login(client, "alice", accounts)
    assert r.status_code == 429
    assert r.json()["detail"] == login_throttle.LOCKED_DETAIL
    assert int(r.headers["Retry-After"]) == login_throttle.BASE_LOCK_SECONDS


def test_a_few_mistakes_do_not_lock(client, accounts, clock):
    fail_times(client, "alice", login_throttle.PAIR_LIMIT - 1)
    assert login(client, "alice", accounts).status_code == 200


def test_lock_is_temporary_and_grows_with_further_failures(client, accounts, clock):
    fail_times(client, "alice", login_throttle.PAIR_LIMIT)
    clock.advance(login_throttle.BASE_LOCK_SECONDS - 1)
    assert login(client, "alice", accounts).status_code == 429
    clock.advance(1)
    # Unlocked; one more wrong guess locks it again, for twice as long.
    fail_times(client, "alice", 1)
    r = login(client, "alice", accounts)
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) == 2 * login_throttle.BASE_LOCK_SECONDS


def test_lock_doubles_up_to_the_cap_and_failures_expire(client, accounts, clock):
    fail_times(client, "alice", login_throttle.PAIR_LIMIT)
    waits = []
    for _ in range(6):
        r = login(client, "alice", accounts)
        assert r.status_code == 429
        waits.append(int(r.headers["Retry-After"]))
        clock.advance(waits[-1])
        fail_times(client, "alice", 1)
    base, cap = login_throttle.BASE_LOCK_SECONDS, login_throttle.MAX_LOCK_SECONDS
    assert waits == [min(cap, base * 2**k) for k in range(6)]
    assert max(waits) == cap
    # An hour later every failure has aged out: a clean slate.
    clock.advance(login_throttle.WINDOW_SECONDS)
    assert login(client, "alice", accounts).status_code == 200


def test_successful_login_resets_the_counter(client, accounts, clock):
    fail_times(client, "alice", login_throttle.PAIR_LIMIT - 1)
    assert login(client, "alice", accounts).status_code == 200
    # Without the reset, a single further failure would lock the account.
    fail_times(client, "alice", login_throttle.PAIR_LIMIT - 1)
    assert login(client, "alice", accounts).status_code == 200


def test_one_locked_account_does_not_affect_another(client, accounts, clock):
    fail_times(client, "alice", login_throttle.PAIR_LIMIT)
    assert login(client, "alice", accounts).status_code == 429
    assert login(client, "bob", accounts).status_code == 200


def test_unknown_usernames_lock_exactly_like_real_ones(client, clock):
    fail_times(client, "nobody_here", login_throttle.PAIR_LIMIT)
    r = login(client, "nobody_here", "anything")
    assert r.status_code == 429
    assert r.json()["detail"] == login_throttle.LOCKED_DETAIL


def test_changing_the_letter_case_does_not_reset_the_count(client, accounts, clock):
    fail_times(client, "alice", login_throttle.PAIR_LIMIT - 1)
    fail_times(client, "ALICE", 1)
    assert login(client, "alice", accounts).status_code == 429


# --- address-aware behaviour --------------------------------------------------


def test_lock_is_per_address_for_a_few_failures(client, accounts, clock, behind_proxy):
    fail_times(client, "alice", login_throttle.PAIR_LIMIT, ip="8.8.8.8")
    assert login(client, "alice", accounts, ip="8.8.8.8").status_code == 429
    # The real owner, elsewhere, is not locked out by someone else's guesses.
    assert login(client, "alice", accounts, ip="1.1.1.1").status_code == 200


def test_rotating_addresses_does_not_buy_more_guesses(client, accounts, clock, behind_proxy):
    for i in range(login_throttle.ACCOUNT_LIMIT):
        fail_times(client, "alice", 1, ip=f"9.9.{i // 200}.{i % 200 + 1}")
    r = login(client, "alice", accounts, ip="4.4.4.4")
    assert r.status_code == 429


def test_rotating_usernames_from_one_address_is_throttled(client, accounts, clock, behind_proxy):
    for i in range(login_throttle.IP_LIMIT):
        fail_times(client, f"spray_{i}", 1, ip="8.8.4.4")
    assert login(client, "bob", accounts, ip="8.8.4.4").status_code == 429
    # Everyone else is unaffected.
    assert login(client, "bob", accounts, ip="1.0.0.1").status_code == 200


def test_a_shared_private_address_is_never_blocked_for_everyone(client, accounts, clock, behind_proxy):
    # A private address here is the proxy or a school NAT: spraying from it
    # still locks each guessed account, but not every learner behind it.
    for i in range(login_throttle.IP_LIMIT):
        fail_times(client, f"spray_{i}", 1, ip="10.0.0.7")
    assert login(client, "bob", accounts, ip="10.0.0.7").status_code == 200


def test_a_forged_forwarded_header_cannot_dodge_the_lock(client, accounts, clock, behind_proxy):
    # The client controls only the left part of X-Forwarded-For; the trusted
    # proxy appends the real address on the right.
    for i in range(login_throttle.PAIR_LIMIT):
        fail_times(client, "carol", 1, ip=f"{i + 20}.1.1.1, 8.8.8.8")
    assert login(client, "carol", accounts, ip="77.7.7.7, 8.8.8.8").status_code == 429


def _request(peer, forwarded=None):
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "headers": headers, "client": (peer, 1234)})


def test_client_ip_resolution(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 0)
    # Direct connection: the header is ignored entirely.
    assert get_client_ip(_request("203.0.113.9", "1.2.3.4")) == "203.0.113.9"
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    assert get_client_ip(_request("172.18.0.5", "1.2.3.4")) == "1.2.3.4"
    assert get_client_ip(_request("172.18.0.5", "6.6.6.6, 1.2.3.4")) == "1.2.3.4"
    # No header: only the trusted peer itself is known.
    assert get_client_ip(_request("172.18.0.5")) == "172.18.0.5"
    monkeypatch.setattr(settings, "trusted_proxy_hops", 2)
    assert get_client_ip(_request("172.18.0.5", "6.6.6.6, 1.2.3.4, 172.18.0.1")) == "1.2.3.4"
    # Garbage is "unknown", never an exception.
    assert get_client_ip(_request("172.18.0.5", "not-an-ip, also-not")) is None


# --- other sign-in paths -------------------------------------------------------


def test_google_sign_in_is_not_blocked_by_a_password_lock(client, accounts, clock, monkeypatch):
    fail_times(client, "bob", login_throttle.PAIR_LIMIT)
    assert login(client, "bob", accounts).status_code == 429

    monkeypatch.setattr(settings, "google_client_id", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(
        auth_router.google_id_token,
        "verify_oauth2_token",
        lambda credential, request, audience: {
            "sub": "google-sub-bob", "email": "bob@example.com", "email_verified": True, "name": "Bob",
        },
    )
    r = client.post("/api/auth/google", json={"credential": "a-google-id-token"})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["username"] == "bob"


def test_registration_still_signs_the_learner_in(client):
    data = register_raw(client, "erin", password="secret1")
    me = expect(client, "get", "/api/me", 200, headers=bearer(data["access_token"]))
    assert me["user"]["username"] == "erin"
    assert login(client, "erin", "secret1").status_code == 200
