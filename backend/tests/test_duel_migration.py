"""Migration a7d3c9e1f402 on a database that already has legacy duels:
statuses are mapped, stored scores survive, the API still serves the old
rows to their players, and downgrade/upgrade round-trips."""

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import database
from app.main import app
from app.security import create_access_token
from helpers import bearer

pytestmark = pytest.mark.migration

BEFORE = "c1e6f3a8d5b2"  # the schema right before real duels


@pytest.fixture
def legacy_duels(legacy_db):
    _url, cfg = legacy_db
    command.upgrade(cfg, BEFORE)
    with database.engine.begin() as c:
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
    return cfg


def test_legacy_statuses_are_mapped_and_scores_kept(legacy_duels):
    with database.engine.connect() as c:
        got = dict(c.execute(text("SELECT id, status FROM duels")).all())
        assert got == {1: "completed", 2: "expired", 3: "cancelled"}, got
        assert c.execute(text("SELECT score FROM duel_participants WHERE duel_id=1 AND user_id=1")).scalar() == 42


def test_downgrade_and_upgrade_round_trip(legacy_duels):
    command.downgrade(legacy_duels, BEFORE)
    with database.engine.connect() as c:
        assert c.execute(text("SELECT status FROM duels WHERE id=1")).scalar() == "finished"
    command.upgrade(legacy_duels, "head")
    with database.engine.connect() as c:
        assert c.execute(text("SELECT status FROM duels WHERE id=1")).scalar() == "completed"


def test_legacy_duels_are_served_read_only_with_their_stored_result(legacy_duels):
    # (after a downgrade round-trip the never-finished legacy duel would be
    # "cancelled": the old schema had no "expired"; here it is "expired")
    with TestClient(app) as client:
        h = bearer(create_access_token(1))
        d = client.get("/api/duels/1", headers=h).json()
        assert d["legacy"] is True and d["status"] == "completed", d
        assert d["result"]["outcome"] == "win" and d["me"]["score"] == 42 and d["opponent"]["score"] == 20, d
        assert d["current"] is None and d["review"] is None
        r = client.post("/api/duels/2/start", headers=h)
        assert r.status_code == 409 and r.json()["code"] == "not_active_expired", r.text
        assert len(client.get("/api/duels", headers=h).json()) == 3
