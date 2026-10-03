"""Learning DNA is shown to learners as the Learning Compass: the seeded
duel texts, the migration for databases that already have them, and the
assistant's prompt no longer say "DNA" -- on a fresh SQLite database."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/compass.db"
os.environ["AI_PROVIDER"] = "offline"

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402

OLD = "Win your first DNA Duel."
NEW = "Win your first Duel."


def texts(db):
    m = db.query(models.Mission).filter_by(slug="first-duel").one()
    a = db.query(models.Achievement).filter_by(code="duel_win").one()
    tr = {(t.content_type, t.locale): t.text for t in db.query(models.ContentTranslation).filter(
        ((models.ContentTranslation.content_type == "mission") & (models.ContentTranslation.content_key == str(m.id)))
        | ((models.ContentTranslation.content_type == "achievement") & (models.ContentTranslation.content_key == str(a.id))))
        if t.field in ("objective", "description")}
    return m, a, tr


def main():
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200

    # ---- a fresh database gets the new text from the seed and the snapshot
    with SessionLocal() as db:
        m, a, tr = texts(db)
        assert m.objective == NEW and a.description == NEW, (m.objective, a.description)
        assert tr[("mission", "ru")] == "Выиграйте свою первую дуэль." and tr[("achievement", "zh")] == "赢得你的第一场对决。", tr
        assert not any("DNA" in v or "ДНК" in v for v in tr.values()), tr
    print("[PASS] a fresh database seeds the duel mission and achievement without 'DNA'")

    # ---- an existing database: put the old seeded text back (as production
    # has it), plus one admin edit, then run the migration
    cfg = Config(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "alembic"))
    command.downgrade(cfg, "f3b8d1c6a274")
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
    print("[PASS] the migration renames the old seeded texts and leaves an admin's edit untouched")

    # ---- the assistant calls the profile by its new name
    from app.services import ai_client
    for locale, name in (("en", "Learning Compass"), ("ru", "Компас обучения"), ("tg", "Қутбнамои омӯзиш"),
                         ("zh", "学习指南针")):
        prompt = ai_client.ASSISTANT_SYSTEM_TEMPLATE.format(
            learner="-", language=ai_client.ASSISTANT_LANGUAGE_NAMES.get(locale, "English"),
            language_detail=ai_client.ASSISTANT_LANGUAGE_DETAIL.get(locale, ""),
            compass=ai_client.ASSISTANT_COMPASS_NAME[locale])
        assert name in prompt and "Learning DNA" not in prompt, locale
    print("[PASS] the assistant knows the profile as the Learning Compass in every locale")

    print("ALL LEARNING COMPASS TESTS PASSED")


if __name__ == "__main__":
    main()
