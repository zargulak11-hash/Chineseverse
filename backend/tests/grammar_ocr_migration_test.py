"""Grammar syllabus OCR fix (alembic b3f7d2a9c614) on a database that has the
scanned errors, as production did: corrected titles keep their ids, every
reference follows (lessons, translations, mistakes), the two folded points
come back as their own topics, user progress stays attached, and a second
run changes nothing."""

import importlib.util
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Chinese in PASS lines on a cp1251 console

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/grammar_ocr.db"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services import practice as practice_svc  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "ocr_migration",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "alembic", "versions", "b3f7d2a9c614_fix_grammar_syllabus_ocr_errors.py"),
)
mig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mig)

# (level, corrupted title, corrected title)
TITLES = [
    (4, "无论⋯⋯，者15/也⋯⋯", "无论⋯⋯，都/也⋯⋯"),
    (5, "尽管⋯⋯，名声/可是⋯⋯", "尽管⋯⋯，但是/可是⋯⋯"),
    (5, "名重词：册、朵、幅、届、颗、匹、扇", "名量词：册、朵、幅、届、颗、匹、扇"),
]
EXAMPLES = [("他还没有舟过什么错", "他还没有出过什么错"), ("太容易舟错了", "太容易出错了"), ("都有自已的优点", "都有自己的优点"),
            ("这己是人人皆知", "这已是人人皆知")]
BAD = ["者15", "名声/可是", "名重词", "舟过", "舟错", "自已", "这己是", "【四29］", "【六47］"]


def level_id(db, level):
    return db.query(models.HSKLevel).filter_by(level=level).one().id


def corrupt(db):
    """Put the database into the scanned state, whatever the snapshot had."""
    for level, bad, good in TITLES:
        g = db.query(models.GrammarTopic).filter_by(hsk_level_id=level_id(db, level)).filter(
            models.GrammarTopic.title.in_([bad, good])).one()
        g.title = bad
        g.pattern = g.pattern.replace("名量词", "名重词").replace("，都/也⋯⋯", "，者15/也⋯⋯").replace("，但是/可是⋯⋯", "，名声/可是⋯⋯")
        for l in db.query(models.Lesson):
            l.summary = (l.summary or "").replace(good, bad)
            l.content = (l.content or "").replace(good, bad).replace("\n名量词\n", "\n名重词\n")
    for good_text, bad_text in [(b, a) for a, b in EXAMPLES]:
        for g in db.query(models.GrammarTopic).filter(models.GrammarTopic.examples.contains(good_text)):
            g.examples = g.examples.replace(good_text, bad_text)
        for l in db.query(models.Lesson).filter(models.Lesson.content.contains(good_text)):
            l.content = l.content.replace(good_text, bad_text)
    for level, prev_title, folded, title, _examples in mig.SPLITS:
        lid = level_id(db, level)
        restored = db.query(models.GrammarTopic).filter_by(hsk_level_id=lid, title=title).first()
        if restored is not None:
            db.query(models.ContentTranslation).filter_by(content_type="grammar_topic", content_key=str(restored.id)).delete()
            db.delete(restored)
        prev = db.query(models.GrammarTopic).filter_by(hsk_level_id=lid, title=prev_title).one()
        if folded not in prev.examples:
            prev.examples += folded
        section = "\n" + folded.replace(folded.split("\n")[1], title, 1)
        for l in db.query(models.Lesson).filter_by(hsk_level_id=lid):
            if section in l.content:
                l.content = l.content.replace(section, folded)
                l.summary = l.summary.replace(f"; {title}", "")
    db.commit()


def everything_text(db):
    rows = [f"{g.title}\n{g.pattern}\n{g.examples}" for g in db.query(models.GrammarTopic)]
    rows += [f"{l.summary}\n{l.content}" for l in db.query(models.Lesson)]
    rows += [t.text for t in db.query(models.ContentTranslation).filter_by(content_type="lesson")]
    rows += [m.reference for m in db.query(models.LearningMistake)]
    return "\n".join(rows)


with TestClient(app) as client:
    reg = client.post("/api/auth/register", json={"username": "ocrlearner", "email": "ocr@example.com", "password": "secret1"})
    assert reg.status_code == 201, reg.text
    uid = reg.json()["user"]["id"]

    with SessionLocal() as db:
        corrupt(db)
        assert all(b in everything_text(db) for b in BAD), "test setup must reproduce the scanned state"
        before = {bad: db.query(models.GrammarTopic).filter_by(title=bad).one().id for _l, bad, _g in TITLES}
        count_before = db.query(models.GrammarTopic).count()
        wuLun = before["无论⋯⋯，者15/也⋯⋯"]
        # A learner who already practiced that point and has it in the mistake bank.
        db.add(models.UserGrammar(user_id=uid, topic_id=wuLun, mastery=40.0, status="learning", times_practiced=4))
        db.add(models.LearningMistake(user_id=uid, mistake_type="grammar", reference="无论⋯⋯，者15/也⋯⋯",
                                      question_text="q", correct_answer="a", priority=2))
        db.add(models.ContentTranslation(content_type="lesson", content_key="999999", field="summary",
                                         locale="ru", text="尽管⋯⋯，名声/可是⋯⋯; x"))
        db.commit()
        cat_tr = db.query(models.ContentTranslation).filter_by(content_type="grammar_topic", content_key=str(wuLun), field="category").count()
        # A copy of a point under its corrected title already exists (as an
        # older curriculum snapshot import would leave it), with a learner on it.
        jin = before["尽管⋯⋯，名声/可是⋯⋯"]
        dup = models.GrammarTopic(hsk_level_id=level_id(db, 5), title="尽管⋯⋯，但是/可是⋯⋯", pattern="x", examples="x")
        db.add(dup)
        db.flush()
        dup_id = dup.id
        other = models.User(username="ocrother", email="ocr2@example.com", password_hash="x")
        db.add(other)
        db.flush()
        other_id = other.id
        db.add(models.UserGrammar(user_id=other_id, topic_id=dup_id, mastery=25.0, status="learning", times_practiced=2))
        db.add(models.ContentTranslation(content_type="grammar_topic", content_key=str(dup_id), field="category", locale="ru", text="dup"))
        db.commit()
    print("[PASS] database reproduces the scanned syllabus (bad titles, examples, folded points, a duplicate)")

    with engine.begin() as conn:
        mig._apply(conn, mig.TEXT_FIXES)
        mig._merge_duplicates(conn, mig.CORRECTED_TITLES)

    with SessionLocal() as db:
        text = everything_text(db)
        assert not any(b in text for b in BAD), [b for b in BAD if b in text]
        for level, bad, good in TITLES:
            g = db.query(models.GrammarTopic).filter_by(hsk_level_id=level_id(db, level), title=good).one()
            assert g.id == before[bad], (good, g.id, before[bad])
            assert db.query(models.GrammarTopic).filter_by(title=bad).count() == 0
        print("[PASS] the 3 titles are corrected on the same rows; the scanned titles no longer exist")
        assert db.get(models.GrammarTopic, dup_id) is None
        moved = db.query(models.UserGrammar).filter_by(user_id=other_id).one()
        assert moved.topic_id == jin and moved.mastery == 25.0
        assert db.query(models.ContentTranslation).filter_by(content_type="grammar_topic", content_key=str(dup_id)).count() == 0
        assert db.query(models.ContentTranslation).filter_by(content_type="grammar_topic", content_key=str(jin), field="category", locale="ru").count() == 1
        print("[PASS] a duplicate under the corrected title is merged into the original row (progress moved, no copy left)")

        for _bad, good in EXAMPLES:
            assert db.query(models.GrammarTopic).filter(models.GrammarTopic.examples.contains(good)).count() == 1, good
        assert "不管⋯⋯，都/也⋯⋯" in text, "the correct neighbouring point is untouched"
        print("[PASS] example OCR fixed: 没有出过什么错 / 容易出错 / 自己的优点 / 这已是人人皆知")

        assert db.query(models.GrammarTopic).count() == count_before + 2
        for level, prev_title, folded, title, examples in mig.SPLITS:
            lid = level_id(db, level)
            restored = db.query(models.GrammarTopic).filter_by(hsk_level_id=lid, title=title).one()
            prev = db.query(models.GrammarTopic).filter_by(hsk_level_id=lid, title=prev_title).one()
            assert restored.examples == examples and restored.pattern == title
            assert restored.category == prev.category and restored.difficulty == prev.difficulty
            assert folded not in prev.examples and prev.examples.strip() and title not in prev.examples
            lesson = next(l for l in db.query(models.Lesson).filter_by(hsk_level_id=lid) if f"\n\n{title}\n" in l.content)
            assert title in lesson.summary and prev_title in lesson.summary
            assert title in [g.title for g in practice_svc.lesson_items(db, lesson)["grammar"]], lesson.title
            assert practice_svc._grammar_example(prev) not in examples
        print("[PASS] the 2 folded points are their own topics again, listed and matched by their lessons")

        u = db.get(models.User, uid)
        ug = db.query(models.UserGrammar).filter_by(user_id=uid).one()
        assert ug.topic_id == wuLun and ug.mastery == 40.0 and ug.times_practiced == 4
        mk = db.query(models.LearningMistake).filter_by(user_id=uid, mistake_type="grammar").one()
        assert mk.reference == "无论⋯⋯，都/也⋯⋯" and mk.priority == 2
        due = [r for t, r in practice_svc._review_items(db, u, 10, practice_svc.datetime.utcnow()) if t == "grammar"]
        assert [r.id for r in due] == [wuLun], "Review still finds the mistake's grammar point"
        assert db.query(models.ContentTranslation).filter_by(content_type="grammar_topic", content_key=str(wuLun), field="category").count() == cat_tr
        lesson150 = next(l for l in db.query(models.Lesson) if "无论⋯⋯，都/也⋯⋯" in (l.summary or ""))
        assert "无论⋯⋯，都/也⋯⋯" in [g.title for g in practice_svc.lesson_items(db, lesson150)["grammar"]]
        print("[PASS] progress, mistake bank, Review lookup, translations and lesson matching follow the same ids")

    snapshot = everything_text(SessionLocal())
    with engine.begin() as conn:
        mig._apply(conn, mig.TEXT_FIXES)
        mig._merge_duplicates(conn, mig.CORRECTED_TITLES)
    with SessionLocal() as db:
        assert everything_text(db) == snapshot and db.query(models.GrammarTopic).count() == count_before + 2
    print("[PASS] running the migration again changes nothing")

    h = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    page = client.get("/api/grammar", params={"hsk_level": 5}, headers=h)
    assert page.status_code == 200 and any(t["title"] == "名量词：册、朵、幅、届、颗、匹、扇" for t in page.json()), page.status_code
    print("[PASS] the grammar page lists the corrected titles")

print("ALL GRAMMAR OCR MIGRATION TESTS PASSED")
