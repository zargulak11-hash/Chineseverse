"""Migration a7d3c9e1f402 on a database that already has legacy duels:
statuses are mapped, stored scores survive, the API still serves the old
rows to their players, and downgrade/upgrade round-trips."""

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

command.upgrade(cfg, "c1e6f3a8d5b2")  # the schema right before real duels
eng = create_engine(URL)
with eng.begin() as c:
    for uid, name in ((1, "old_a"), (2, "old_b")):
        c.execute(text(
            "INSERT INTO users (id, username, email, password_hash, is_active, total_xp, coins, is_admin, created_at) "
            "VALUES (:i, :n, :e, 'x', 1, 0, 0, 0, CURRENT_TIMESTAMP)"), {"i": uid, "n": name, "e": f"{name}@example.com"})
    for did, status, winner in ((1, "finished", 1), (2, "active", None), (3, "aborted", None)):
        c.execute(text("INSERT INTO duels (id, status, question_data, winner_id, created_at) "
                       "VALUES (:i, :s, '{\"questions\": []}', :w, CURRENT_TIMESTAMP)"), {"i": did, "s": status, "w": winner})
        c.execute(text("INSERT INTO duel_participants (duel_id, user_id, role, score, correct_count, answered, finished) "
                       "VALUES (:d, 1, 'challenger', 42, 4, 5, 1), (:d, 2, 'opponent', 20, 2, 5, 1)"), {"d": did})

command.upgrade(cfg, "head")
with eng.connect() as c:
    got = dict(c.execute(text("SELECT id, status FROM duels")).all())
    assert got == {1: "completed", 2: "expired", 3: "cancelled"}, got
    assert c.execute(text("SELECT score FROM duel_participants WHERE duel_id=1 AND user_id=1")).scalar() == 42
print("[PASS] legacy statuses mapped (finished->completed, active->expired, aborted->cancelled), scores kept")

command.downgrade(cfg, "c1e6f3a8d5b2")
with eng.connect() as c:
    assert c.execute(text("SELECT status FROM duels WHERE id=1")).scalar() == "finished"
command.upgrade(cfg, "head")
print("[PASS] downgrade and re-upgrade round-trip")

# The API serves the legacy completed duel to its players, read-only.
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.security import create_access_token  # noqa: E402

with TestClient(app) as client:
    h = {"Authorization": f"Bearer {create_access_token(1)}"}
    d = client.get("/api/duels/1", headers=h).json()
    assert d["legacy"] is True and d["status"] == "completed", d
    assert d["result"]["outcome"] == "win" and d["me"]["score"] == 42 and d["opponent"]["score"] == 20, d
    assert d["current"] is None and d["review"] is None
    # (after the downgrade round-trip the never-finished legacy duel is
    # "cancelled": the old schema had no "expired", so downgrade folds it
    # into "aborted")
    r = client.post("/api/duels/2/start", headers=h)
    assert r.status_code == 409 and r.json()["code"] == "not_active_cancelled", r.text
    assert len(client.get("/api/duels", headers=h).json()) == 3
print("[PASS] legacy duels are listed and shown read-only with their stored result")
print("ALL DUEL MIGRATION TESTS PASSED")
