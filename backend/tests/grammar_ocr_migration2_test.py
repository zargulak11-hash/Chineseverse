"""Second grammar syllabus OCR fix (alembic d8e2a5c1f736) on a database that
still has the scanned text, as production does: all 17 corrections land,
titles keep their ids, lessons / translations / mistakes follow, learner
progress stays attached, correct look-alike text is untouched, a fresh
database (corrected snapshot) already has the right text, and a second run
changes nothing."""

import importlib.util
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/grammar_ocr2.db"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "ocr_migration2",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "alembic", "versions", "d8e2a5c1f736_fix_more_grammar_syllabus_ocr_errors.py"),
)
mig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mig)

G = models.GrammarTopic


def text_of(db):
    rows = [f"{g.title}\n{g.pattern}\n{g.examples}" for g in db.query(G)]
    rows += [f"{l.summary}\n{l.content}" for l in db.query(models.Lesson)]
    rows += [t.text for t in db.query(models.ContentTranslation)]
    rows += [m.reference for m in db.query(models.LearningMistake)]
    return "\n".join(rows)


with TestClient(app) as client:
    reg = client.post("/api/auth/register", json={"username": "ocr2learner", "email": "ocr2@example.com", "password": "secret1"})
    assert reg.status_code == 201, reg.text
    uid = reg.json()["user"]["id"]

    with SessionLocal() as db:
        fresh = text_of(db)
        assert all(new in fresh for _old, new in mig.TEXT_FIXES), [n for _o, n in mig.TEXT_FIXES if n not in fresh]
        assert not any(old in fresh for old, _new in mig.TEXT_FIXES)
        print("[PASS] a fresh database (corrected snapshot) has all 17 corrections and none of the scan errors")

        # Put the scanned text back, as production still has it.
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
        neg = db.query(G).filter_by(title="否定副词：另、不、没、没有").one()
        neg_id = neg.id
        db.add(models.UserGrammar(user_id=uid, topic_id=neg_id, mastery=35.0, status="learning", times_practiced=3))
        db.add(models.LearningMistake(user_id=uid, mistake_type="grammar", reference="否定副词：另、不、没、没有",
                                      question_text="q", correct_answer="a", priority=1))
        db.add(models.ContentTranslation(content_type="grammar_topic", content_key=str(neg_id), field="title",
                                         locale="ru", text="否定副词：另、不、没、没有 — отрицание"))
        db.commit()
        scanned = text_of(db)
        assert all(old in scanned for old, _new in mig.TEXT_FIXES)
        count = db.query(G).count()
        # Correct text that merely looks similar must survive.
        lookalike = db.query(G).filter(G.examples.contains("一家")).count()
    print("[PASS] the database reproduces the scanned syllabus, with progress and a mistake on a corrupted title")

    with engine.begin() as conn:
        mig.apply(conn)

    with SessionLocal() as db:
        text = text_of(db)
        assert not any(old in text for old, _new in mig.TEXT_FIXES), [o for o, _n in mig.TEXT_FIXES if o in text]
        assert all(new in text for _old, new in mig.TEXT_FIXES)
        g = db.get(G, neg_id)
        assert g.title == "否定副词：别、不、没、没有" and db.query(G).count() == count
        ug = db.query(models.UserGrammar).filter_by(user_id=uid).one()
        assert ug.topic_id == neg_id and ug.mastery == 35.0 and ug.times_practiced == 3
        assert db.query(models.LearningMistake).filter_by(user_id=uid).one().reference == "否定副词：别、不、没、没有"
        tr = db.query(models.ContentTranslation).filter_by(content_type="grammar_topic", content_key=str(neg_id), field="title").one()
        assert tr.text.startswith("否定副词：别")
        assert db.query(G).filter(G.examples.contains("一家")).count() == lookalike
        assert db.query(G).filter(G.examples.contains("他来中国之前")).count() == 1
        assert db.query(G).filter(G.examples.contains("亚健康")).count() == 1
    print("[PASS] all 17 corrections applied on the same rows; progress, mistake bank and translations follow; look-alikes untouched")

    snap = text_of(SessionLocal())
    with engine.begin() as conn:
        mig.apply(conn)
    assert text_of(SessionLocal()) == snap
    print("[PASS] running it again changes nothing")

    h = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    page = client.get("/api/grammar", params={"hsk_level": 1}, headers=h)
    assert any(t["title"] == "否定副词：别、不、没、没有" for t in page.json()), page.status_code
    print("[PASS] the grammar list shows the corrected title")

print("ALL GRAMMAR OCR MIGRATION 2 TESTS PASSED")
