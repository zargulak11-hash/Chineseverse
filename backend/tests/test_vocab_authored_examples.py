"""Hand-written word examples (app/seed_content/vocab_examples) are held to
scripts/seed_vocab_authored_examples.py's checks on a freshly seeded
database, and reach it through the curriculum snapshot: the example, its
pinyin and English on the word, Russian and Tajik as drafts awaiting a
native speaker's review."""

from app import models
from app.database import SessionLocal
from scripts import seed_vocab_authored_examples as authored


def test_every_authored_example_passes_the_checks(client):
    entries = authored.entries()
    assert len(entries) >= 40
    with SessionLocal() as db:
        checker, seen = authored.Checker(db), set()
        problems = [p for e in entries for p in checker.problems(e, seen)]
    assert problems == [], problems[:10]


def test_a_fresh_database_gets_them_with_draft_translations(client):
    with SessionLocal() as db:
        level_of = {l.id: l.level for l in db.query(models.HSKLevel)}
        for e in authored.entries():
            row = next(w for w in db.query(models.VocabularyWord).filter_by(simplified=e["word"])
                       if level_of[w.hsk_level_id] == e["level"])
            assert (row.example, row.example_pinyin, row.example_translation) == (e["zh"], e["pinyin"], e["en"])
            trs = {t.locale: t for t in db.query(models.ContentTranslation).filter_by(
                content_type="vocab_word", content_key=str(row.id), field="example_translation")}
            assert trs["ru"].text == e["ru"] and trs["tg"].text == e["tg"]
            assert trs["ru"].source == trs["tg"].source == "draft"


def test_the_checks_refuse_a_wrong_reading_a_hidden_word_and_a_hard_word(client):
    # 休息 has no example yet: only the change made in each case is judged.
    good = {"level": 1, "word": "休息", "zh": "我们在那儿休息。", "pinyin": "wǒmen zài nàr xiūxi.",
            "en": "x", "ru": "где", "tg": "куҷо"}
    with SessionLocal() as db:
        c = authored.Checker(db)

        def why(**change):
            # "Already has an example" is left out: later batches give these
            # words their examples; every other refusal is still asserted.
            return " ".join(p for p in c.problems({**good, **change}, set()) if "already has" not in p)

        assert why() == ""
        assert "pinyin" in why(pinyin="wǒmen zài nǎr xiūxi.")          # wrong tone (哪 for 那)
        assert "pinyin" in why(pinyin="wǒmen zài xiūxi.")               # syllable missing
        assert "whole word" in why(word="分钟", zh="我们休息十分钟吧。",  # 十分 hides 分钟
                                   pinyin="wǒmen xiūxi shí fēnzhōng ba.")
        assert "above HSK 1" in why(zh="我们在这儿休息，很近。", pinyin="wǒmen zài zhèr xiūxi, hěn jìn.")
        assert "no tg" in why(tg="")
        assert "pinyin" in why(pinyin="women zai nar xiuxi.")              # no tone marks at all
        assert "not exactly one HSK 3 row" in why(level=3)                 # word is not HSK 3
        assert "Cyrillic" in why(ru="where", tg="where")                   # ru/tg in the wrong script
        assert "Chinese left" in why(ru="После 不 нужно")                   # a stray character
        assert "Cyrillic in the English" in why(en="не English")
        # 可爱 is stored "kě ài": joined, it needs the apostrophe.
        cute = next(w for w in c.rows["可爱"])
        cute_level = c.level_of[cute.hsk_level_id]
        apostrophe = {"level": cute_level, "word": "可爱", "zh": "她很可爱。"}
        assert "apostrophe" in why(**apostrophe, pinyin="tā hěn kěài.")
        assert "apostrophe" not in why(**apostrophe, pinyin="tā hěn kě'ài.")
        # The same sentence twice in one batch, or reusing a word's example.
        seen = set()
        c.problems(good, seen)  # first use of the sentence
        assert any("used twice" in p for p in c.problems(good, seen))
        taken = next(iter(c.existing))
        assert "used twice" in why(zh=taken)
