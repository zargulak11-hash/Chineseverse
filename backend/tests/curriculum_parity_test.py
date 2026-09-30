"""A fresh database (what a new deployment gets: migrations + seed_all on
startup) must end up with the full committed curriculum, identically on a
second startup (idempotent), with translations attached to the right rows."""

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/curriculum.db"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import func  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_all  # noqa: E402

# Real HSK 3.0 cumulative targets, per-level (non-cumulative) row counts.
EXPECTED_HANZI = {1: 300, 2: 300, 3: 300, 4: 300, 5: 300, 6: 300, 7: 1200}


def snapshot(db):
    return {
        "vocab": db.query(models.VocabularyWord).count(),
        "grammar": db.query(models.GrammarTopic).count(),
        "lessons": db.query(models.Lesson).count(),
        "hanzi": db.query(models.Hanzi).count(),
        "translations": db.query(models.ContentTranslation).count(),
    }


with TestClient(app) as client:
    with SessionLocal() as db:
        first = snapshot(db)
        print("after first startup:", first)
        assert first["vocab"] >= 11092, first
        assert first["grammar"] >= 572, first
        assert first["lessons"] >= 100, first
        assert first["hanzi"] == 3000, first
        assert first["translations"] >= 5000, first
        per_level = dict(
            db.query(models.HSKLevel.level, func.count(models.Hanzi.id))
            .join(models.Hanzi).group_by(models.HSKLevel.level).all()
        )
        assert per_level == EXPECTED_HANZI, per_level
        for lvl in range(1, 8):
            level = db.query(models.HSKLevel).filter_by(level=lvl).one()
            assert db.query(models.Lesson).filter_by(hsk_level_id=level.id).count() > 0, lvl
            assert db.query(models.GrammarTopic).filter_by(hsk_level_id=level.id).count() > 0, lvl
        print("[PASS] every HSK level/band has vocab, grammar, lessons and the real Hanzi counts")

        t0 = time.time()
        seed_all(db)
        second = snapshot(db)
        assert second == first, (first, second)
        print(f"[PASS] second seed run is a no-op ({time.time() - t0:.1f}s)")

    # Translations resolved onto THIS database's ids, not the exporter's.
    ru = {"X-Locale": "ru"}
    reg = client.post("/api/auth/register", json={"username": "parity", "email": "parity@example.com", "password": "secret1"}).json()
    h = {"Authorization": f"Bearer {reg['access_token']}", **ru}
    words = client.get("/api/vocab?hsk_level=1", headers=h).json()
    ni = next(w for w in words if w["simplified"] == "你")
    assert ni["meanings"] and all(ord(c) < 0x3000 for c in ni["meanings"]) and any("Ѐ" <= c <= "ӿ" for c in ni["meanings"]), ni
    levels = client.get("/api/hsk/levels", headers=ru).json()
    assert any("Ѐ" <= c <= "ӿ" for c in levels[0]["description"]), levels[0]
    print(f"[PASS] ru translations resolve on a fresh DB: 你 -> {ni['meanings']!r}")

print("ALL CURRICULUM PARITY TESTS PASSED")
