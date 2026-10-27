"""POST /api/auth/register is capped per public address
(services/signup_throttle.py): enough for a classroom behind one router,
not for a script creating accounts or probing which emails exist."""

from pathlib import Path

import pytest

from app.deps import get_client_ip
from app.main import app
from app.services import signup_throttle
from helpers import unique_name


@pytest.fixture
def from_ip(monkeypatch):
    """from_ip(address) makes the next requests come from that address.
    Real public addresses: the documentation ranges (203.0.113.0/24, ...)
    are not is_global, so they are never limited, by design."""
    def use(address):
        monkeypatch.setitem(app.dependency_overrides, get_client_ip, lambda: address)
    return use


@pytest.fixture
def clock(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(signup_throttle, "_now", lambda: now[0])
    return now


def register(client, name=None, email=None):
    name = name or unique_name("signup")
    return client.post("/api/auth/register", json={
        "username": name, "email": email or f"{name}@example.com", "password": "secret1"})


def test_a_public_address_gets_a_generous_allowance_then_a_429(client, from_ip, clock):
    from_ip("8.8.8.8")
    for _ in range(signup_throttle.LIMIT_PER_HOUR):
        assert register(client).status_code == 201
    r = register(client)
    assert r.status_code == 429
    assert r.json()["detail"] == signup_throttle.LIMITED_DETAIL
    assert int(r.headers["Retry-After"]) > 0
    # Another address is unaffected, and the window slides.
    from_ip("1.1.1.1")
    assert register(client).status_code == 201
    from_ip("8.8.8.8")
    clock[0] += signup_throttle.WINDOW_SECONDS + 1
    assert register(client).status_code == 201


def test_refused_attempts_count_too_so_emails_cannot_be_walked(client, from_ip, clock):
    from_ip("9.9.9.9")
    taken = unique_name("taken")
    assert register(client, taken).status_code == 201
    for _ in range(signup_throttle.LIMIT_PER_HOUR - 1):
        # "email already registered" is the answer an email-walker reads.
        assert register(client, email=f"{taken}@example.com").status_code == 409
    # Limited before any lookup: the same answer whatever the email.
    assert register(client, email=f"{taken}@example.com").status_code == 429
    assert register(client, email="never-seen@example.com").status_code == 429


@pytest.mark.parametrize("address", [None, "10.0.0.5", "127.0.0.1", "192.168.1.20"])
def test_private_or_unknown_addresses_are_never_limited(client, from_ip, clock, address):
    # Our own proxy or a shared NAT: limiting it would lock out everyone.
    from_ip(address)
    for _ in range(signup_throttle.LIMIT_PER_HOUR + 3):
        assert register(client).status_code == 201


def test_the_429_is_a_sentence_the_app_translates():
    # frontend/src/apiErrors.js maps exact sentences; see test_email_linking.
    api_errors = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "apiErrors.js").read_text(encoding="utf-8")
    assert f'"{signup_throttle.LIMITED_DETAIL}": "signupLimited"' in api_errors


def test_logins_are_not_counted_against_sign_ups(client, from_ip, clock):
    from_ip("8.8.4.4")
    name = unique_name("loginonly")
    assert register(client, name).status_code == 201
    for _ in range(signup_throttle.LIMIT_PER_HOUR + 5):
        r = client.post("/api/auth/login", json={"username": name, "password": "secret1"})
        assert r.status_code == 200
    assert register(client).status_code == 201
