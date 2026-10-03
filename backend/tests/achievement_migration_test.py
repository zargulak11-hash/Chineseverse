"""Migration b5e2d8a4c193 on a database that already has unlocks: they are
backfilled as already announced (no flood of old "Achievement unlocked!"
notes after the deploy), nothing is lost, and downgrade/upgrade round-trips."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
URL = f"sqlite:///{_tmp}/legacy.db"
os.environ["DATABASE_URL"] = URL

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = Config(os.path.join(HERE, "alembic.ini"))
cfg.set_main_option("script_location", os.path.join(HERE, "alembic"))
cfg.set_main_option("sqlalchemy.url", URL)
command.upgrade(cfg, "a4c7e2d9f1b3")
eng = create_engine(URL)
with eng.begin() as c:
    c.execute(text("INSERT INTO users (id, username, email, password_hash, is_active, total_xp, coins, is_admin, created_at) "
                   "VALUES (1, 'old', 'old@example.com', 'x', 1, 0, 0, 0, CURRENT_TIMESTAMP)"))
    c.execute(text("INSERT INTO achievements (id, code, title, icon, category) VALUES (1, 'streak_7', 't', 'i', 'habit')"))
    c.execute(text("INSERT INTO user_achievements (user_id, achievement_id, unlocked_at) "
                   "VALUES (1, 1, '2026-01-02 03:04:05')"))
command.upgrade(cfg, "head")
with eng.begin() as c:
    rows = c.execute(text("SELECT unlocked_at, notified_at FROM user_achievements")).all()
    assert len(rows) == 1 and str(rows[0][1]).startswith("2026-01-02 03:04:05"), rows
command.downgrade(cfg, "a4c7e2d9f1b3")
command.upgrade(cfg, "head")
print("[PASS] migration backfills existing unlocks as already announced; round-trips")
print("ALL ACHIEVEMENT MIGRATION TESTS PASSED")
