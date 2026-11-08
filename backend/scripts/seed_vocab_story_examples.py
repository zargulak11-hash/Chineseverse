# -*- coding: utf-8 -*-
"""Example sentences for vocabulary, taken from the Chinese Stories library
-- sentences a person wrote and translated, never generated for this.

Of 11,334 words only 430 had an example (from the HSK grammar syllabus,
scripts/seed_vocab_syllabus_examples.py), and none had a translation. The
119 graded books (app/seed_content/books) are sentences written for
learners at a known HSK level, each with its English, Russian and Tajik
translation. A word without an example gets one of them when all of this
holds:

- the book is at the word's own HSK level or below, and every other word
  of the sentence is at that level or below too (a beginner's example must
  be readable by a beginner);
- the word is a whole word of the sentence: both a forward and a backward
  longest-match split into curriculum words have it at the same place
  (学 is not "found" in 学生, nor 生活 in 学生活动);
- the word has one spelling-to-reading in the curriculum, and so does every
  other word and character of the sentence (还 hái / huán, 长 cháng / zhǎng
  are left out): the pinyin is the story reader's own (stories.pinyin_of,
  curriculum readings and the book's names), so it is only used where the
  curriculum cannot be read two ways;
- it is a plain sentence of 5-22 characters ending in 。！？, preferring
  ones without quoted speech or names, close to 12 characters.

The English translation goes in example_translation, Russian and Tajik in
content translations (field "example_translation"). A word that already
has an example is never touched. Re-export the curriculum snapshot
afterwards; its import fills empty examples on every database:
    python scripts/seed_vocab_story_examples.py [--dry-run]
    python scripts/export_curriculum_snapshot.py
"""
import collections
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.services import books, stories  # noqa: E402
from app.services import sentence as sent  # noqa: E402
from app.services.localization import set_translation  # noqa: E402

CJK = re.compile(r"[㐀-鿿]")
# No quoted speech: an example must stand on its own.
PLAIN = re.compile(r"^[㐀-鿿，、：；！？。]+[。！？]$")
MAX_WORD = 8
# The pinyin of existing examples uses ASCII punctuation ("wǒ shì xuéshēng."),
# as practice rounds do (sentence.py); the reader's pinyin keeps the Chinese.
ASCII_PUNCT = str.maketrans({"，": ",", "、": ",", "。": ".", "！": "!", "？": "?", "：": ":", "；": ";"})


def _join_syllables(pinyin: str) -> str:
    """One word's syllables written together, with the apostrophe pinyin
    requires before a syllable that starts with a, o or e (bǎo'ān, dá'àn --
    "bǎoān" could be read bǎo-ān or bǎ-oān)."""
    out = ""
    for syl in (pinyin or "").split():
        if out and unicodedata.normalize("NFD", syl)[0].lower() in "aoe":
            out += "'"
        out += syl
    return out


def _example_pinyin(db, source: dict, zh: str) -> str:
    """The story reader's pinyin (stories.pinyin_of: curriculum readings,
    the source's names), written one word at a time: the curriculum stores
    some words spaced ("dòng wù") and some not ("xīguā"), and an example
    mixing both read badly. Readings are unchanged; names keep their space
    ("Wáng Xiǎoyǔ")."""
    toks = stories.segment(db, source, zh)
    hz = sent.hanzi_rows(db, {t["text"] for t in toks if t["kind"] == "char"})
    parts: list[str] = []
    for t in toks:
        if t["kind"] == "name":
            parts.append(t["pinyin"])
        elif t["word"] is not None:
            parts.append(_join_syllables(t["word"].pinyin))
        elif t["kind"] == "char" and t["text"] in hz:
            parts.append(hz[t["text"]].pinyin or "")
        elif t["kind"] == "other" and parts:
            parts[-1] += t["text"]
    return _pinyin_text(" ".join(p for p in parts if p))


def _pinyin_text(p: str) -> str:
    p = p.translate(ASCII_PUNCT)
    p = re.sub(r"\s+([,.!?:;])", r"\1", p)
    return re.sub(r"([,!?:;])(?=\S)", r"\1 ", re.sub(r"\s+", " ", p)).strip()


def corpus():
    """(source, sentence) for every translated sentence written for learners:
    the stories library and the detective case files (same shape: a level,
    names with their pinyin, sentences in zh/en/ru/tg)."""
    from app.services import case_files

    for book in books.all_books():
        for ch in book["chapters"]:
            for s in ch["sentences"]:
                yield book, s
    for case in case_files.all_cases():
        for s in case["sentences"]:
            yield case, s


def _reading(p: str) -> str:
    """A reading compared loosely: no spaces, no case, tones kept."""
    return unicodedata.normalize("NFC", re.sub(r"[\s'’·-]", "", p or "").lower())


def _split(text: str, lexicon: set[str], backward: bool) -> list[tuple[int, str]]:
    """(start, piece) of a longest-match split; chars outside the lexicon
    stand alone."""
    out, n = [], len(text)
    if not backward:
        i = 0
        while i < n:
            size = next((s for s in range(min(MAX_WORD, n - i), 1, -1) if text[i:i + s] in lexicon), 1)
            out.append((i, text[i:i + size]))
            i += size
        return out
    j = n
    while j > 0:
        size = next((s for s in range(min(MAX_WORD, j), 1, -1) if text[j - s:j] in lexicon), 1)
        out.append((j - size, text[j - size:j]))
        j -= size
    return out[::-1]


def main(dry_run: bool) -> None:
    db = SessionLocal()
    level_of = {l.id: l.level for l in db.query(models.HSKLevel)}
    words = db.query(models.VocabularyWord).all()
    by_spelling: dict[str, list[models.VocabularyWord]] = collections.defaultdict(list)
    for w in words:
        by_spelling[w.simplified].append(w)
    readings = {s: {_reading(w.pinyin) for w in rows} for s, rows in by_spelling.items()}
    for h in db.query(models.Hanzi):
        # A character's own row may list several readings ("hái, huán").
        readings.setdefault(h.character, set()).update(
            _reading(r) for r in re.split(r"[,，/;；]", h.pinyin or "") if r.strip())
    ambiguous = {s for s, r in readings.items() if len(r) > 1}
    lexicon = set(by_spelling)
    lowest = {s: min(rows, key=lambda w: (level_of[w.hsk_level_id], w.id)) for s, rows in by_spelling.items()}
    char_level = {h.character: level_of[h.hsk_level_id] for h in db.query(models.Hanzi)}

    # Every usable story sentence, with the words a both-ways split agrees on.
    candidates: dict[str, list[tuple]] = collections.defaultdict(list)
    for book, s in corpus():
        names = book.get("names") or {}
        zh = s["zh"]
        n_cjk = len(CJK.findall(zh))
        if not PLAIN.match(zh) or not 5 <= n_cjk <= 22 or not all(s.get(k) for k in ("en", "ru", "tg")):
            continue
        masked = zh
        for name in sorted(names, key=len, reverse=True):
            masked = masked.replace(name, "□" * len(name))
        fwd = set(_split(masked, lexicon, False))
        agreed = [(i, p) for i, p in _split(masked, lexicon, True) if (i, p) in fwd]
        pieces = [p for _, p in _split(masked, lexicon, False) if CJK.search(p)]
        if any(p in ambiguous for p in pieces):
            continue
        levels = [level_of[lowest[p].hsk_level_id] if p in lowest else char_level.get(p, 99) for p in pieces]
        has_name = "□" in masked
        for _, p in agreed:
            if p in lexicon:
                others = max([lv for q, lv in zip(pieces, levels) if q != p] or [0])
                candidates[p].append((book, s, others, has_name, n_cjk, False))

    filled = collections.Counter()
    total = collections.Counter()
    samples = []
    for w in words:
        level = level_of[w.hsk_level_id]
        total[level] += 1
        if w.example or lowest.get(w.simplified) is not w or w.simplified in ambiguous:
            continue
        options = [c for c in candidates.get(w.simplified, [])
                   if c[0]["level"] <= level and c[2] <= level]
        if not options:
            continue
        book, s, _, has_name, n_cjk, quoted = min(
            options, key=lambda c: (c[5], c[3], abs(c[4] - 12), c[0]["slug"], c[1]["zh"]))
        filled[level] += 1
        pinyin = _example_pinyin(db, book, s["zh"])
        if len(samples) < 12 and level <= 3 and filled[level] % 40 == 1:
            samples.append((level, w.simplified, s["zh"], pinyin, s["en"], s["ru"], s["tg"]))
        if not dry_run:
            w.example, w.example_pinyin, w.example_translation = s["zh"], pinyin, s["en"]
            db.flush()
            for loc in ("ru", "tg"):
                set_translation(db, "vocab_word", str(w.id), "example_translation", loc, s[loc])

    for lv in sorted(total):
        have = sum(1 for w in words if level_of[w.hsk_level_id] == lv and w.example)
        print(f"HSK {lv}: {filled[lv]} new examples; {have + (filled[lv] if dry_run else 0)} of {total[lv]} words would have one")
    print("total new:", sum(filled.values()))
    for x in samples:
        print("  ", x)
    if dry_run:
        db.rollback()
    else:
        db.commit()


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
