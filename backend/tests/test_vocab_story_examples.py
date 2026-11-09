"""Word examples taken from the stories and case files
(scripts/seed_vocab_story_examples.py) come with a translation: the
snapshot's examples are checked as content, and /api/vocab serves the
translation in the learner's language."""

import gzip
import json
import re

import pytest

from app import models
from app.database import SessionLocal
from helpers import expect, register, unique_name
from test_band7_word_fix_migration import SNAPSHOT, _syllables

CJK = re.compile(r"[㐀-鿿]")


@pytest.fixture(scope="module")
def snapshot():
    return json.loads(gzip.open(SNAPSHOT, "rt", encoding="utf-8").read())


@pytest.fixture(scope="module")
def translated(snapshot):
    """The examples taken from stories and cases -- not the hand-written
    ones (test_vocab_authored_examples.py checks those)."""
    from scripts import seed_vocab_authored_examples as authored

    written = {(e["level"], e["word"]) for e in authored.entries()}
    return [v for v in snapshot["vocab"]
            if v.get("example_translation") and (v["level"], v["simplified"]) not in written]


def test_hundreds_of_words_have_a_translated_example(translated):
    assert len(translated) >= 450
    assert sum(1 for v in translated if v["level"] == 1) >= 150


def test_each_example_shows_its_word_with_pinyin_for_every_character(translated):
    bad = []
    for v in translated:
        zh, py = v["example"], v["example_pinyin"] or ""
        syl = _syllables(re.sub(r"[:;!?]", " ", py))
        chars = len(CJK.findall(zh))
        erhua = zh.count("儿")
        if v["simplified"] not in zh or syl is None or not (chars - erhua <= len(syl) <= chars):
            bad.append((v["simplified"], zh, py))
        # Pinyin in the examples' own style: ASCII punctuation, words joined.
        if re.search(r"[，。！？：；、]", py) or "  " in py:
            bad.append(("punctuation", zh, py))
    # The syllable count above also catches a joined word missing its
    # apostrophe ("bǎoān" for bǎo'ān does not split into two syllables).
    assert bad == [], bad[:10]
    assert bad == [], bad[:10]


def test_each_example_is_translated_into_russian_and_tajik(snapshot, translated):
    have = {(t[1], t[3]) for t in snapshot["translations"]
            if t[0] == "vocab_word" and t[2] == "example_translation"}
    missing = [(v["simplified"], loc) for v in translated for loc in ("ru", "tg")
               if (f"{v['level']}|{v['simplified']}", loc) not in have]
    assert missing == [], missing[:10]


def test_examples_are_readable_at_the_words_level(client, translated):
    # A beginner's example uses beginner words: every curriculum word of an
    # HSK 1 example, split the way the story reader splits it (the sources'
    # people and places, like 上海, are names, not vocabulary), is HSK 1.
    from app.services import books, case_files, stories

    source = {}  # sentence -> the book or case it came from (its own names)
    for book in books.all_books():
        for ch in book["chapters"]:
            for s in ch["sentences"]:
                source.setdefault(s["zh"], book)
    for case in case_files.all_cases():
        for s in case["sentences"]:
            source.setdefault(s["zh"], case)
    with SessionLocal() as db:
        levels = {l.id: l.level for l in db.query(models.HSKLevel)}
        for v in (v for v in translated if v["level"] == 1):
            assert v["example"] in source, v["example"]  # every one is a real story/case sentence
            toks = stories.segment(db, source[v["example"]], v["example"])
            words = [t["word"] for t in toks if t["word"] is not None]
            above = [(w.simplified, levels[w.hsk_level_id]) for w in words if levels[w.hsk_level_id] > 1]
            assert above == [], (v["example"], above)


def test_the_api_serves_the_translation_in_the_learners_language(client):
    _, h = register(client, unique_name("examples"))
    with SessionLocal() as db:
        word = (db.query(models.VocabularyWord)
                .filter(models.VocabularyWord.example_translation.isnot(None)).order_by(models.VocabularyWord.id).first())
        level = db.get(models.HSKLevel, word.hsk_level_id).level
        ru = (db.query(models.ContentTranslation)
              .filter_by(content_type="vocab_word", content_key=str(word.id), field="example_translation", locale="ru")
              .one().text)

    def get(locale):
        rows = expect(client, "get", f"/api/vocab?hsk_level={level}", 200, headers={**h, "X-Locale": locale})
        return next(r for r in rows if r["id"] == word.id)

    assert get("en")["example_translation"] == word.example_translation
    assert get("ru")["example_translation"] == ru and ru != word.example_translation
    assert get("tg")["example_translation"]
    # Chinese UI: the sentence is already in Chinese.
    zh = get("zh")
    assert zh["example_translation"] is None and zh["example"] == word.example
