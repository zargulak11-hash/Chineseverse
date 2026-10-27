"""Migration b8d1f4a6c3e9 (users.email_verified_at) on a database from
before it: accounts already bound to Google or GitHub got their address
from that provider and count as proven; password-only accounts do not, and
downgrade/upgrade round-trips."""

from datetime import datetime

import pytest
from alembic import command
from sqlalchemy import text

from app import database

pytestmark = pytest.mark.migration

BEFORE = "e7b3c9d2f418"
INSERT = text(
    "INSERT INTO users (username, email, password_hash, google_sub, github_id, is_active, created_at) "
    "VALUES (:u, :e, 'x', :g, :h, :a, :c)"
)
EXPECTED = {"pwonly": False, "viagoogle": True, "viagithub": True}


def verified():
    with database.engine.begin() as c:
        rows = c.execute(text("SELECT username, email_verified_at FROM users")).all()
    return {username: at is not None for username, at in rows}


def test_provider_accounts_count_as_proven_and_password_accounts_do_not(legacy_db):
    _url, cfg = legacy_db
    command.upgrade(cfg, BEFORE)
    with database.engine.begin() as c:
        for username, google_sub, github_id in (
            ("pwonly", None, None), ("viagoogle", "g-1", None), ("viagithub", None, "7"),
        ):
            c.execute(INSERT, {"u": username, "e": f"{username}@example.com", "g": google_sub,
                               "h": github_id, "a": True, "c": datetime.utcnow()})
    command.upgrade(cfg, "head")
    assert verified() == EXPECTED
    command.downgrade(cfg, BEFORE)
    command.upgrade(cfg, "head")
    assert verified() == EXPECTED
