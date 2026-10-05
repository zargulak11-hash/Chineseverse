"""Learning DNA is shown to learners as the Learning Compass: the seeded
duel texts, the migration for databases that already have them, and the
assistant's prompt no longer say "DNA"."""

import pytest
from alembic import command

from app import models
from app.database import SessionLocal
from app.services import ai_client
from conftest import alembic_config

OLD = "Win your first DNA Duel."
NEW = "Win your first Duel."
BEFORE = "f3b8d1c6a274"  # the revision before the rename


def texts(db):
    m = db.query(models.Mission).filter_by(slug="first-duel").one()
    a = db.query(models.Achievement).filter_by(code="duel_win").one()
    tr = {(t.content_type, t.locale): t.text for t in db.query(models.ContentTranslation).filter(
        ((models.ContentTranslation.content_type == "mission") & (models.ContentTranslation.content_key == str(m.id)))
        | ((models.ContentTranslation.content_type == "achievement") & (models.ContentTranslation.content_key == str(a.id))))
        if t.field in ("objective", "description")}
    return m, a, tr


def test_a_fresh_database_seeds_the_duel_texts_without_dna(client):
    with SessionLocal() as db:
        m, a, tr = texts(db)
        assert m.objective == NEW and a.description == NEW, (m.objective, a.description)
        assert tr[("mission", "ru")] == "Выиграйте свою первую дуэль." and tr[("achievement", "zh")] == "赢得你的第一场对决。", tr
        assert not any("DNA" in v or "ДНК" in v for v in tr.values()), tr


@pytest.mark.migration
def test_the_migration_renames_old_seeded_texts_and_spares_an_admin_edit(client):
    # An existing database: the old seeded text back (as production had it),
    # plus one admin edit, then the migration.
    cfg = alembic_config()
    command.downgrade(cfg, BEFORE)
    with SessionLocal() as db:
        m, a, tr = texts(db)
        assert m.objective == OLD and a.description == OLD, "downgrade restores the old text"
        assert tr[("mission", "ru")] == "Выиграйте свою первую ДНК-дуэль.", tr
        edited = (db.query(models.ContentTranslation)
                  .filter_by(content_type="achievement", content_key=str(a.id), field="description", locale="tg").one())
        edited.text = "Матни админ: ДНК-дуэл"
        db.commit()
    command.upgrade(cfg, "head")
    with SessionLocal() as db:
        m, a, tr = texts(db)
        assert m.objective == NEW and a.description == NEW
        assert tr[("mission", "ru")] == "Выиграйте свою первую дуэль." and tr[("mission", "zh")] == "赢得你的第一场对决。", tr
        assert tr[("achievement", "tg")] == "Матни админ: ДНК-дуэл", "an admin-edited text must be left alone"


@pytest.mark.parametrize("locale, name", [
    ("en", "Learning Compass"), ("ru", "Компас обучения"), ("tg", "Қутбнамои омӯзиш"), ("zh", "学习指南针"),
])
def test_the_assistant_calls_the_profile_the_learning_compass(locale, name):
    prompt = ai_client.ASSISTANT_SYSTEM_TEMPLATE.format(
        learner="-", language=ai_client.ASSISTANT_LANGUAGE_NAMES.get(locale, "English"),
        language_detail=ai_client.ASSISTANT_LANGUAGE_DETAIL.get(locale, ""),
        compass=ai_client.ASSISTANT_COMPASS_NAME[locale])
    assert name in prompt and "Learning DNA" not in prompt, locale
