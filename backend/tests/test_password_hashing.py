"""Password hash cost and its upgrade (security.needs_rehash).

New hashes use settings.password_hash_iterations; a hash made with fewer
rounds (every account from before the count was raised) is replaced at the
learner's next successful sign-in, with the same password. The suite runs
at a low cost (conftest); these tests raise it with monkeypatch to play a
hash from before the raise against the current setting."""

from datetime import datetime

import pytest

from app import models
from app.config import settings
from app.database import SessionLocal
from app.routers import auth as auth_router
from app.security import hash_password, needs_rehash, verify_password
from helpers import bearer, expect, register_raw, unique_name

OLD_COST, NEW_COST = 1000, 2000


@pytest.fixture
def raised_cost(monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", NEW_COST)


def stored_hash(username):
    with SessionLocal() as db:
        return db.query(models.User).filter_by(username=username).one().password_hash


def set_old_hash(username, password, changed_at=None):
    """Store a hash made at OLD_COST, as an account from before the raise has."""
    with SessionLocal() as db:
        user = db.query(models.User).filter_by(username=username).one()
        user.password_hash = hash_password(password)  # settings still at OLD_COST here
        user.password_changed_at = changed_at
        db.commit()


def login(client, username, password):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def test_production_default_meets_the_owasp_minimum():
    from app.config import Settings

    assert Settings.model_fields["password_hash_iterations"].default >= 600_000


def test_new_hashes_record_the_configured_cost(raised_cost):
    stored = hash_password("pw-123456")
    assert stored.startswith(f"pbkdf2_sha256${NEW_COST}$")
    assert verify_password("pw-123456", stored)
    assert not needs_rehash(stored)


def test_needs_rehash_only_for_cheaper_well_formed_hashes(monkeypatch):
    old = hash_password("pw")
    monkeypatch.setattr(settings, "password_hash_iterations", NEW_COST)
    assert needs_rehash(old)
    assert not needs_rehash(hash_password("pw"))
    # Garbage is never "upgraded" -- it can't be verified in the first place.
    assert not needs_rehash("garbage-without-separators")
    assert not needs_rehash("pbkdf2_sha256$not-a-number$aa$bb")


def test_sign_in_upgrades_an_old_hash_and_keeps_the_password(client, monkeypatch):
    name = unique_name("rehash")
    register_raw(client, name, password="old-cost-pass")
    set_old_hash(name, "old-cost-pass")
    assert stored_hash(name).startswith(f"pbkdf2_sha256${OLD_COST}$")

    monkeypatch.setattr(settings, "password_hash_iterations", NEW_COST)
    r = login(client, name, "old-cost-pass")
    assert r.status_code == 200, r.text
    upgraded = stored_hash(name)
    assert upgraded.startswith(f"pbkdf2_sha256${NEW_COST}$")
    assert verify_password("old-cost-pass", upgraded)
    # And the same password keeps working against the new hash.
    assert login(client, name, "old-cost-pass").status_code == 200
    assert stored_hash(name) == upgraded  # nothing left to upgrade


def test_the_upgrade_is_not_a_password_change(client, monkeypatch):
    """password_changed_at ends every session issued before it; an upgrade
    the learner never asked for must not sign their other devices out."""
    name = unique_name("rehash")
    first = register_raw(client, name, password="keep-sessions")
    stamp = datetime(2026, 1, 1)
    set_old_hash(name, "keep-sessions", changed_at=stamp)

    monkeypatch.setattr(settings, "password_hash_iterations", NEW_COST)
    assert login(client, name, "keep-sessions").status_code == 200
    with SessionLocal() as db:
        user = db.query(models.User).filter_by(username=name).one()
        assert user.password_changed_at == stamp
    expect(client, "get", "/api/me", 200, headers=bearer(first["access_token"]))


def test_a_wrong_password_never_upgrades(client, monkeypatch):
    name = unique_name("rehash")
    register_raw(client, name, password="right-pass")
    set_old_hash(name, "right-pass")
    before = stored_hash(name)

    monkeypatch.setattr(settings, "password_hash_iterations", NEW_COST)
    assert login(client, name, "wrong-pass").status_code == 401
    assert stored_hash(name) == before


def test_a_wrong_password_on_an_old_hash_is_topped_up_to_full_cost(client, monkeypatch):
    """An unknown username costs NEW_COST rounds; a wrong password against
    an old hash must too, or the faster answer names a real account."""
    name = unique_name("rehash")
    register_raw(client, name, password="right-pass")
    set_old_hash(name, "right-pass")
    monkeypatch.setattr(settings, "password_hash_iterations", NEW_COST)

    burns = []
    real = auth_router.burn_password_check
    monkeypatch.setattr(
        auth_router, "burn_password_check",
        lambda pw, already_spent=None: (burns.append(already_spent), real(pw, already_spent=already_spent)),
    )
    assert login(client, name, "wrong-pass").status_code == 401
    assert burns == [stored_hash(name)]
    assert login(client, unique_name("ghost"), "wrong-pass").status_code == 401
    assert burns[-1] is None
