"""Migration b5e2d8a4c193 on a database that already has unlocks: they are
backfilled as already announced (no flood of old "Achievement unlocked!"
notes after the deploy), nothing is lost, and downgrade/upgrade round-trips."""

import pytest
from alembic import command
from sqlalchemy import text

from app import database

pytestmark = pytest.mark.migration

BEFORE = "a4c7e2d9f1b3"  # the schema right before notified_at


def test_existing_unlocks_are_backfilled_as_announced_and_the_migration_round_trips(legacy_db):
    _url, cfg = legacy_db
    command.upgrade(cfg, BEFORE)
    with database.engine.begin() as c:
        c.execute(text("INSERT INTO users (id, username, email, password_hash, is_active, total_xp, coins, is_admin, created_at) "
                       "VALUES (1, 'old', 'old@example.com', 'x', 1, 0, 0, 0, CURRENT_TIMESTAMP)"))
        c.execute(text("INSERT INTO achievements (id, code, title, icon, category) VALUES (1, 'streak_7', 't', 'i', 'habit')"))
        c.execute(text("INSERT INTO user_achievements (user_id, achievement_id, unlocked_at) "
                       "VALUES (1, 1, '2026-01-02 03:04:05')"))
    command.upgrade(cfg, "head")
    with database.engine.begin() as c:
        rows = c.execute(text("SELECT unlocked_at, notified_at FROM user_achievements")).all()
    assert len(rows) == 1 and str(rows[0][1]).startswith("2026-01-02 03:04:05"), rows
    command.downgrade(cfg, BEFORE)
    command.upgrade(cfg, "head")
    with database.engine.begin() as c:
        assert c.execute(text("SELECT count(*) FROM user_achievements")).scalar() == 1
