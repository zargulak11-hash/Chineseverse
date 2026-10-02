"""Content quality on a fresh database seeded from the curriculum snapshot:
vocabulary readings (alembic c8e4a1f6b2d9), lesson-word translations,
syllabus example sentences, lesson bodies without the English word list,
listening by meaning, zh labels that do not give answers away, and the
placement tone question."""

import importlib.util
import os
import re
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Chinese in PASS lines on a cp1251 console

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/content_quality.db"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.routers.duels import _build_questions  # noqa: E402
from app.services import practice as practice_svc  # noqa: E402
from app.services.lesson_path import ordered_lessons  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "readings_migration",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "alembic", "versions", "c8e4a1f6b2d9_fix_vocabulary_wrong_readings.py"),
)
readings = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(readings)

REFERENCE = re.compile(r"^(surname |variant of |old variant of |see |used in |abbr\. for )", re.I)


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, f"{method.upper()} {url} -> {resp.status_code}: {resp.text[:300]}"
    return resp.json() if resp.content else None


def register(client, name):
    data = expect(client, "post", "/api/auth/register", 201,
                  json={"username": name, "email": f"{name}@example.com", "password": "secret1"})
    return data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}


def word(db, level, simplified):
    lid = db.query(models.HSKLevel).filter_by(level=level).one().id
    return db.query(models.VocabularyWord).filter_by(hsk_level_id=lid, simplified=simplified).one()


with TestClient(app) as client:
    uid, h = register(client, "cqlearner")

    # ------------------------------------------------ readings on a fresh database
    with SessionLocal() as db:
        checks = [(1, "打", "dǎ", "hit"), (2, "离", "lí", "leave"), (1, "后", "hòu", "behind"), (1, "白", "bái", "white"),
                  (2, "鸟", "niǎo", "bird"), (1, "大学", "dà xué", "university"), (1, "要", "yào", "want"),
                  (1, "吧", "ba", "particle"), (1, "干", "gàn", "to do"), (3, "白", "bái", "in vain")]
        for level, w, py, sense in checks:
            row = word(db, level, w)
            assert row.pinyin == py and sense in row.meanings, (w, row.pinyin, row.meanings)
        assert word(db, 7, "略").pinyin == "lüè"
        left = [w.simplified for w in db.query(models.VocabularyWord) if REFERENCE.match((w.meanings or "").split(";")[0].strip())]
        assert len(left) == 9, left  # source entries with no real sense at all, documented in the migration
        assert not [w.simplified for w in db.query(models.VocabularyWord) if re.search(r"u:|˙|\d", w.pinyin)]
        assert word(db, 7, "离谱儿").pinyin == "lí pǔr" and word(db, 7, "离谱儿").meanings.startswith("outrageous")
        # Grammar questions show an example sentence, never a syllabus heading or note.
        notes = [g.title for g in db.query(models.GrammarTopic)
                 if practice_svc._grammar_example(g) and practice_svc._SYLLABUS_NOTE.search(practice_svc._grammar_example(g))]
        assert not notes, notes[:5]
    print("[PASS] fresh database: 打 dǎ, 离 lí, 后 behind, 鸟 bird, 大学 university, 吧 ba; no malformed pinyin; grammar prompts are sentences")

    # ------------------------------------------------ the readings migration on old data
    with SessionLocal() as db:
        fixes = readings.load_fixes()
        sample = [f for f in fixes if (f[0], f[1]) in {(1, "打"), (2, "离"), (2, "鸟"), (1, "白")}]
        assert len(sample) == 4, sample
        for level, w, old_py, old_m, _np, _nm in sample:
            row = word(db, level, w)
            row.pinyin, row.meanings = old_py, old_m
        edited = word(db, 1, "后")
        edited.pinyin, edited.meanings = "Hòu", "an admin's own text"  # not the imported value -> untouched
        db.commit()
    with engine.begin() as conn:
        assert readings.apply(conn) == 4
    with engine.begin() as conn:
        assert readings.apply(conn) == 0
    with SessionLocal() as db:
        er = word(db, 1, "二")
        er.example, er.example_pinyin = "两个人。", "liǎng ge rén."
        db.commit()
    with engine.begin() as conn:
        assert readings.apply_examples(conn) == 1 and readings.apply_examples(conn) == 0
    with SessionLocal() as db:
        assert word(db, 1, "打").pinyin == "dǎ" and word(db, 2, "鸟").meanings.startswith("bird")
        assert word(db, 1, "后").meanings == "an admin's own text"
        assert word(db, 1, "二").example == "十二 二十 二百 两百"
    print("[PASS] readings migration fixes the imported rows, leaves an edited row alone, runs once")

    # ------------------------------------------------ translations of every lesson word
    with SessionLocal() as db:
        have = {(int(t.content_key), t.locale) for t in db.query(models.ContentTranslation).filter_by(content_type="vocab_word", field="meanings")}
        lesson_words = {w.id: w for lesson, _l in ordered_lessons(db) for w in practice_svc.lesson_items(db, lesson)["vocab"]}
        missing = [w.simplified for wid, w in lesson_words.items() if (wid, "ru") not in have or (wid, "tg") not in have]
        assert not missing, missing[:10]
        texts = [t.text for t in db.query(models.ContentTranslation).filter_by(content_type="vocab_word")]
        assert not [x for x in texts if re.search(r"TODO|lorem|translation unavailable|placeholder", x, re.I)]
    by = {x["simplified"]: x["meanings"] for lv in (7, 8, 9)
          for x in expect(client, "get", "/api/vocab", 200, headers={**h, "X-Locale": "ru"}, params={"hsk_level": lv})}
    assert by.get("书籍") == "книги, литература", by.get("书籍")
    print(f"[PASS] all {len(lesson_words)} lesson words have ru and tg meanings (HSK 1-9), served in the learner's locale")

    # ------------------------------------------------ syllabus example sentences
    with SessionLocal() as db:
        withex = [w for w in db.query(models.VocabularyWord) if w.example]
        assert len(withex) >= 400, len(withex)
        for w in withex:
            assert w.simplified in w.example, (w.simplified, w.example)
        assert word(db, 3, "敢").example == "我不敢在河里游泳。"
        assert word(db, 7, "皆").example == "这已是人人皆知的事实。"
        assert word(db, 4, "得").example is None  # 得 has several readings: no unverified sentence
        assert word(db, 7, "该").example is None  # HSK 7 该 is not HSK 2's modal 该
    print(f"[PASS] {len(withex)} words carry an official syllabus sentence that contains them; ambiguous ones get none")

    # ------------------------------------------------ lesson body without the English word list
    with SessionLocal() as db:
        lessons = {l.title: l for l in db.query(models.Lesson)}
        greet, g1 = lessons["Greetings"], lessons["HSK1 Grammar 1"]
        db.add(models.Progress(user_id=uid, lesson_id=greet.id, status="completed", score=100, completed_at=datetime.utcnow()))
        db.commit()
        g1_id, raw = g1.id, g1.content
        round_before = [r.id for _t, r in practice_svc.lesson_round_items(db, g1)]
    assert "New vocabulary:" in raw
    body = expect(client, "get", f"/api/lessons/{g1_id}", 200, headers=h)["content"]
    assert "New vocabulary" not in body and body == practice_svc.lesson_body(raw) and body.strip()
    assert raw.split("New vocabulary:")[0].strip() == body.strip()
    for loc in ("ru", "tg", "zh"):
        localized = expect(client, "get", f"/api/lessons/{g1_id}", 200, headers={**h, "X-Locale": loc})["content"]
        assert "New vocabulary" not in localized and "我是学生" in localized, loc
        assert not re.search(r"[A-Za-z]{2,}", localized), (loc, re.findall(r"[A-Za-z]{2,}", localized)[:5])
    items = expect(client, "get", f"/api/lessons/{g1_id}/items", 200, headers={**h, "X-Locale": "ru"})
    block_words = practice_svc._lesson_phrases(raw.split("New vocabulary:")[1])
    assert set(block_words) <= {v["simplified"] for v in items["vocab"]}, "every listed word is still a card"
    with SessionLocal() as db:
        assert [r.id for _t, r in practice_svc.lesson_round_items(db, db.get(models.Lesson, g1_id))] == round_before
        u = db.get(models.User, uid)
        u.is_admin = True
        db.commit()
    assert "New vocabulary:" in expect(client, "get", f"/api/lessons/{g1_id}", 200, headers=h)["content"]
    with SessionLocal() as db:
        db.get(models.User, uid).is_admin = False
        db.commit()
    print("[PASS] learners read lessons without the English 'New vocabulary:' list; cards and practice unchanged; admins get raw text")

    # ------------------------------------------------ listening by meaning, graded by the server
    listen = []
    for _ in range(6):
        s = expect(client, "post", "/api/practice/sessions", 201, headers=h, json={"source": "vocab", "hsk_level": 2, "size": 12})
        listen += [(s["id"], q) for q in s["questions"] if q["type"] == "listen_to_word"]
        if len(listen) >= 3:
            break
    assert listen, "rounds include listening questions"
    with SessionLocal() as db:
        for sid, q in listen:
            words = {db.get(models.VocabularyWord, o["id"]).simplified for o in q["options"]}
            labels = [o["label"] for o in q["options"]]
            assert q["prompt"]["speak"] not in labels and not (set(labels) & words), labels
            assert all(not re.search(r"[㐀-鿿]{2,}", lbl) or lbl not in words for lbl in labels)
            stored = db.get(models.PracticeSession, sid).questions[q["index"]]
            assert stored["item_id"] not in [None] and "item_id" not in q
    sid, q = listen[0]
    with SessionLocal() as db:
        correct_id = db.get(models.PracticeSession, sid).questions[q["index"]]["item_id"]
    wrong_id = next(o["id"] for o in q["options"] if o["id"] != correct_id)
    r = expect(client, "post", f"/api/practice/sessions/{sid}/answer", 200, headers=h, json={"index": q["index"], "choice_id": wrong_id})
    assert r["correct"] is False and r["correct_id"] == correct_id
    if len(listen) > 1:
        sid2, q2 = listen[1]
        with SessionLocal() as db:
            right = db.get(models.PracticeSession, sid2).questions[q2["index"]]["item_id"]
        assert expect(client, "post", f"/api/practice/sessions/{sid2}/answer", 200, headers=h,
                      json={"index": q2["index"], "choice_id": right})["correct"] is True
    print(f"[PASS] {len(listen)} listening questions offer meanings, never the spoken word; the server grades them")

    # ------------------------------------------------ zh labels never give the answer away
    zh = {**h, "X-Locale": "zh"}
    s = expect(client, "post", "/api/practice/sessions", 201, headers=zh, json={"source": "vocab", "hsk_level": 1, "size": 20})
    with SessionLocal() as db:
        for q in s["questions"]:
            if q["type"] == "meaning_to_word":
                assert q["prompt"]["text"] not in [o["label"] for o in q["options"]], q
            if q["type"] in ("word_to_meaning", "listen_to_word"):
                for o in q["options"]:
                    assert o["label"] != db.get(models.VocabularyWord, o["id"]).simplified, o
    print("[PASS] zh practice: a meaning is never just the word itself, so options do not reveal answers")

    # ------------------------------------------------ placement tone question
    with SessionLocal() as db:
        lid = db.query(models.HSKLevel).filter_by(level=1).one().id
        tones = [q for _ in range(30) for q in _build_questions(db, lid) if q["type"] == "tone"]
        assert tones, "tone questions are still asked"
        for q in tones:
            ch = re.search(r"「(.+)」", q["prompt"]).group(1)
            assert len(ch) == 1 and "(" not in q["prompt"] and not re.search(r"[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]", q["prompt"]), q["prompt"]
    print("[PASS] placement tone questions ask about one character and no longer print its pinyin")

print("ALL CONTENT QUALITY TESTS PASSED")
