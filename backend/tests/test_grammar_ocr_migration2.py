"""Second grammar syllabus OCR fix (alembic d8e2a5c1f736) on a database that
still has the scanned text, as production does: all 17 corrections land,
titles keep their ids, lessons / translations / mistakes follow, learner
progress stays attached, correct look-alike text is untouched, a fresh
database (corrected snapshot) already has the right text, and a second run
changes nothing."""

import importlib.util
import os
from types import SimpleNamespace

import pytest

from app import database, models
from app.database import SessionLocal
from helpers import bearer, register_raw

pytestmark = pytest.mark.migration

_spec = importlib.util.spec_from_file_location(
    "ocr_migration2",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "alembic", "versions", "d8e2a5c1f736_fix_more_grammar_syllabus_ocr_errors.py"),
)
mig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mig)

G = models.GrammarTopic
NEG_SCANNED = "否定副词：另、不、没、没有"
NEG_FIXED = "否定副词：别、不、没、没有"


def text_of(db):
    rows = [f"{g.title}\n{g.pattern}\n{g.examples}" for g in db.query(G)]
    rows += [f"{l.summary}\n{l.content}" for l in db.query(models.Lesson)]
    rows += [t.text for t in db.query(models.ContentTranslation)]
    rows += [m.reference for m in db.query(models.LearningMistake)]
    return "\n".join(rows)


def run_migration():
    with database.engine.begin() as conn:
        mig.apply(conn)


def test_a_fresh_database_already_has_every_correction(client):
    with SessionLocal() as db:
        fresh = text_of(db)
    assert all(new in fresh for _old, new in mig.TEXT_FIXES), [n for _o, n in mig.TEXT_FIXES if n not in fresh]
    assert not any(old in fresh for old, _new in mig.TEXT_FIXES)


@pytest.fixture(scope="module")
def migrated(client):
    """Put the scanned text back (as production still has it) with a learner
    on a corrupted title, then run the migration once."""
    reg = register_raw(client, "ocr2learner")
    uid = reg["user"]["id"]
    with SessionLocal() as db:
        for old, new in mig.TEXT_FIXES:
            for g in db.query(G):
                for col in ("title", "pattern", "examples"):
                    v = getattr(g, col)
                    if v and new in v:
                        setattr(g, col, v.replace(new, old))
            for l in db.query(models.Lesson):
                l.summary = (l.summary or "").replace(new, old)
                l.content = (l.content or "").replace(new, old)
        db.commit()
        neg_id = db.query(G).filter_by(title=NEG_SCANNED).one().id
        db.add(models.UserGrammar(user_id=uid, topic_id=neg_id, mastery=35.0, status="learning", times_practiced=3))
        db.add(models.LearningMistake(user_id=uid, mistake_type="grammar", reference=NEG_SCANNED,
                                      question_text="q", correct_answer="a", priority=1))
        db.add(models.ContentTranslation(content_type="grammar_topic", content_key=str(neg_id), field="title",
                                         locale="ru", text=f"{NEG_SCANNED} — отрицание"))
        db.commit()
        assert all(old in text_of(db) for old, _new in mig.TEXT_FIXES), "setup must reproduce the scanned state"
        count = db.query(G).count()
        # Correct text that merely looks similar must survive.
        lookalike = db.query(G).filter(G.examples.contains("一家")).count()
    run_migration()
    return SimpleNamespace(uid=uid, token=reg["access_token"], neg_id=neg_id, count=count, lookalike=lookalike)


def test_all_corrections_land_on_the_same_rows(migrated):
    with SessionLocal() as db:
        text = text_of(db)
        assert not any(old in text for old, _new in mig.TEXT_FIXES), [o for o, _n in mig.TEXT_FIXES if o in text]
        assert all(new in text for _old, new in mig.TEXT_FIXES)
        assert db.get(G, migrated.neg_id).title == NEG_FIXED
        assert db.query(G).count() == migrated.count


def test_progress_mistakes_and_translations_follow(migrated):
    with SessionLocal() as db:
        ug = db.query(models.UserGrammar).filter_by(user_id=migrated.uid).one()
        assert ug.topic_id == migrated.neg_id and ug.mastery == 35.0 and ug.times_practiced == 3
        assert db.query(models.LearningMistake).filter_by(user_id=migrated.uid).one().reference == NEG_FIXED
        tr = db.query(models.ContentTranslation).filter_by(
            content_type="grammar_topic", content_key=str(migrated.neg_id), field="title").one()
        assert tr.text.startswith("否定副词：别")


def test_look_alike_correct_text_is_untouched(migrated):
    with SessionLocal() as db:
        assert db.query(G).filter(G.examples.contains("一家")).count() == migrated.lookalike
        assert db.query(G).filter(G.examples.contains("他来中国之前")).count() == 1
        assert db.query(G).filter(G.examples.contains("亚健康")).count() == 1


def test_running_it_again_changes_nothing(migrated):
    with SessionLocal() as db:
        snap = text_of(db)
    run_migration()
    with SessionLocal() as db:
        assert text_of(db) == snap


def test_the_grammar_list_shows_the_corrected_title(client, migrated):
    page = client.get("/api/grammar", params={"hsk_level": 1}, headers=bearer(migrated.token))
    assert page.status_code == 200
    assert any(t["title"] == NEG_FIXED for t in page.json())
