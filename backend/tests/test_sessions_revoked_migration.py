"""Migration d4a9c2e7f150 (users.sessions_revoked_at) on a database from
before it: the column arrives empty, so no existing session is ended by the
upgrade, and downgrade/upgrade round-trips."""

from datetime import datetime

import pytest
from alembic import command
from sqlalchemy import inspect, text

from app import database

pytestmark = pytest.mark.migration

BEFORE = "b8d1f4a6c3e9"


def has_column():
    return "sessions_revoked_at" in {c["name"] for c in inspect(database.engine).get_columns("users")}


def test_the_column_arrives_empty_and_round_trips(legacy_db):
    _url, cfg = legacy_db
    command.upgrade(cfg, BEFORE)
    assert not has_column()
    with database.engine.begin() as c:
        c.execute(text("INSERT INTO users (username, email, password_hash, is_active, created_at) "
                       "VALUES ('before', 'before@example.com', 'x', :a, :c)"), {"a": True, "c": datetime.utcnow()})
    command.upgrade(cfg, "head")
    database.engine.dispose()
    assert has_column()
    with database.engine.begin() as c:
        # Null = never used: deps.session_ended refuses nothing for this account.
        assert c.execute(text("SELECT sessions_revoked_at FROM users WHERE username = 'before'")).scalar() is None
    command.downgrade(cfg, BEFORE)
    database.engine.dispose()
    assert not has_column()
    command.upgrade(cfg, "head")
    database.engine.dispose()
    assert has_column()
