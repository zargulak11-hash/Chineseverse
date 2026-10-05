"""A fresh database (what a new deployment gets: migrations + seed_all on
startup) must end up with the full committed curriculum, identically on a
second startup (idempotent), with translations attached to the right rows.

The session's template database is built exactly that way (conftest), and
this module's copy has been through a second startup already."""

from sqlalchemy import func

from app import models
from app.database import SessionLocal
from app.seed import seed_all
from helpers import register

# Real HSK 3.0 per-level (non-cumulative) Hanzi row counts; 7 = the shared 7-9 band.
EXPECTED_HANZI = {1: 300, 2: 300, 3: 300, 4: 300, 5: 300, 6: 300, 7: 1200}


def snapshot(db):
    return {
        "vocab": db.query(models.VocabularyWord).count(),
        "grammar": db.query(models.GrammarTopic).count(),
        "lessons": db.query(models.Lesson).count(),
        "hanzi": db.query(models.Hanzi).count(),
        "translations": db.query(models.ContentTranslation).count(),
    }


def test_fresh_database_has_the_full_curriculum(client):
    with SessionLocal() as db:
        first = snapshot(db)
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
        # HSK 7-9 is one shared band: no separate rows for 8 or 9.
        assert db.query(models.HSKLevel).filter(models.HSKLevel.level.in_((8, 9))).count() == 0


def test_seeding_again_is_a_no_op(client):
    with SessionLocal() as db:
        first = snapshot(db)
        seed_all(db)
        assert snapshot(db) == first


def test_translations_resolve_onto_this_databases_ids(client):
    # Not the exporter's ids: the snapshot is natural-keyed.
    ru = {"X-Locale": "ru"}
    _, h = register(client, "parity")
    words = client.get("/api/vocab?hsk_level=1", headers={**h, **ru}).json()
    ni = next(w for w in words if w["simplified"] == "你")
    assert ni["meanings"] and all(ord(c) < 0x3000 for c in ni["meanings"]), ni
    assert any("Ѐ" <= c <= "ӿ" for c in ni["meanings"]), ni
    levels = client.get("/api/hsk/levels", headers=ru).json()
    assert any("Ѐ" <= c <= "ӿ" for c in levels[0]["description"]), levels[0]
