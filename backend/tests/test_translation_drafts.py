"""Dictionary meanings written to close the Russian/Tajik/Chinese gap are
marked "draft" for native review; the old Chinese "meanings" that were only
the word itself (喝 -> 喝) are removed; and a Chinese quiz uses real Chinese
definitions without pointing at the answer."""

import gzip
import json
import re

import pytest

from app import models
from app.database import SessionLocal
from app.services.curriculum import SNAPSHOT_PATH
from helpers import expect, register, unique_name

CJK = re.compile(r"[㐀-鿿]")
LATIN = re.compile(r"[A-Za-z]{3,}")


def test_drafts_keep_their_mark_through_the_snapshot_import(client):
    snap = json.load(gzip.open(SNAPSHOT_PATH, "rt", encoding="utf-8"))
    drafts = [t for t in snap["translations"] if len(t) > 5]
    assert drafts and all(t[5] == "draft" for t in drafts)
    # no Chinese "meaning" that is only the word itself
    assert not [t for t in snap["translations"]
                if t[:4] and t[0] == "vocab_word" and t[3] == "zh" and t[4] == t[1].split("|", 1)[1]]
    with SessionLocal() as db:
        CT = models.ContentTranslation
        assert db.query(CT).filter(CT.source == "draft").count() == len(drafts)
        # an authored translation stays unmarked
        word = db.query(models.VocabularyWord).filter_by(simplified="喝").first()
        ru = db.query(CT).filter_by(content_type="vocab_word", content_key=str(word.id), locale="ru").one()
        assert ru.text == "пить" and ru.source is None


@pytest.mark.parametrize("level", [1, 2, 3])
def test_every_beginner_word_has_a_meaning_in_every_language(client, level):
    with SessionLocal() as db:
        level_id = db.query(models.HSKLevel.id).filter_by(level=level).scalar()
        ids = {str(i) for (i,) in db.query(models.VocabularyWord.id).filter_by(hsk_level_id=level_id)}
        for locale in ("ru", "tg", "zh"):
            have = {k for (k,) in db.query(models.ContentTranslation.content_key).filter_by(
                content_type="vocab_word", field="meanings", locale=locale)}
            assert not ids - have, (level, locale, len(ids - have))


def test_a_chinese_quiz_is_in_chinese_and_never_points_at_the_answer(client):
    _, h = register(client, unique_name("zhquiz"))
    zh = {**h, "X-Locale": "zh"}
    for _ in range(3):
        s = expect(client, "post", "/api/practice/sessions", 201, headers=zh,
                   json={"source": "vocab", "hsk_level": 1, "size": 10})
        for i, q in enumerate(s["questions"]):
            labels = {o["id"]: o["label"] for o in q["options"]}
            if q["type"] == "word_to_meaning":
                word = q["prompt"]["text"]
                assert all(CJK.search(l) and not LATIN.search(l) for l in labels.values()), labels
                # The right definition must not contain the word itself (it is
                # written "～"). A WRONG option may: 早饭 "早上吃的饭" is a
                # fair distractor when the word is 吃.
                a = expect(client, "post", f"/api/practice/sessions/{s['id']}/answer", 200, headers=zh,
                           json={"index": i, "choice_id": next(iter(labels)), "response_ms": 1000})
                assert word not in labels[a["correct_id"]], (word, labels[a["correct_id"]])
            if q["type"] == "meaning_to_word":
                assert CJK.search(q["prompt"]["text"]) and not LATIN.search(q["prompt"]["text"]), q["prompt"]
