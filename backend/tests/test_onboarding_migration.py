"""Migration b6d4e8f2a915: accounts that were already in use before the app
started enforcing onboarding are marked onboarded, so they are not stopped
and asked the questions again; a genuinely new account is left in it."""

import pytest
from alembic import command
from sqlalchemy import text

from app import database

pytestmark = pytest.mark.migration

BEFORE = "d8e2a5c1f736"  # the schema right before the backfill


@pytest.fixture
def legacy_accounts(legacy_db):
    _url, cfg = legacy_db
    command.upgrade(cfg, BEFORE)
    with database.engine.begin() as c:
        def user(uid, xp=0, profile=True, done=False):
            c.execute(text(
                "INSERT INTO users (id, username, email, password_hash, is_active, total_xp, coins, is_admin, created_at) "
                "VALUES (:i, :n, :e, 'x', 1, :xp, 0, 0, CURRENT_TIMESTAMP)"),
                {"i": uid, "n": f"old_{uid}", "e": f"old_{uid}@example.com", "xp": xp})
            if profile:
                c.execute(text("INSERT INTO user_profiles (user_id, onboarding_completed) VALUES (:i, :d)"),
                          {"i": uid, "d": done})

        user(1)                      # registered, never used the app
        user(2, xp=40)               # earned XP
        user(3, profile=False)       # old account with no profile row, but activity
        c.execute(text("INSERT INTO activity_events (user_id, section, action_type, minutes, created_at) "
                       "VALUES (3, 'practice', 'practice_answer', 0.5, CURRENT_TIMESTAMP)"))
        user(4, done=True)           # finished onboarding through the app
        user(5)                      # started the placement test, never finished it
        c.execute(text("INSERT INTO placement_attempts (user_id, status) VALUES (5, 'active')"))
        user(6)                      # skipped the placement test
        c.execute(text("INSERT INTO placement_attempts (user_id, status) VALUES (6, 'skipped')"))
        user(7, profile=False)       # no profile row and no use at all
    command.upgrade(cfg, "head")
    return cfg


def test_accounts_in_use_are_onboarded_and_new_ones_are_not(legacy_accounts):
    with database.engine.connect() as c:
        got = {uid: bool(done) for uid, done in c.execute(
            text("SELECT user_id, onboarding_completed FROM user_profiles")).all()}
    assert got == {1: False, 2: True, 3: True, 4: True, 5: False, 6: True}, got


def test_downgrade_keeps_the_flags(legacy_accounts):
    command.downgrade(legacy_accounts, BEFORE)
    with database.engine.connect() as c:
        assert c.execute(text("SELECT onboarding_completed FROM user_profiles WHERE user_id=2")).scalar()
