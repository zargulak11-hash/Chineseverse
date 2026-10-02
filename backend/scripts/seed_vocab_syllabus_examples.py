# -*- coding: utf-8 -*-
"""Example sentences for vocabulary, taken from the official HSK 3.0 grammar
syllabus -- never written by hand.

The source vocabulary (drkameleon/complete-hsk-vocabulary) carries no
example sentences: 54 of 11,334 words had one. The grammar syllabus
(grammar_topics.examples) is the HSK 3.0 standard's own sentences, and a
grammar point whose title names a word ("能愿动词：会、能", "时间副词：刚、
刚刚、已经") gives sentences written to show exactly that word. A word gets
the shortest such sentence when all of this holds:

- the grammar point is at the word's own HSK level or below -- and at
  exactly its level when the same word also has a lower-level row, which
  is learned for another sense (HSK 7 该 "this (formal)" is not HSK 2's
  modal 该 "should");
- the sentence is a plain Chinese sentence (no "X", "⋯", "+", brackets --
  those lines are patterns, not sentences), 4-30 characters;
- the word is a whole word of the sentence, not part of a longer one
  (正 is not "found" in 他们正在唱歌, 东 not in 东边);
- a character with several readings (得 dé / de / děi, 还 hái / huán)
  only gets a sentence whose grammar title names this row's reading --
  the sentence alone cannot say which reading it uses. The readings come
  from the source dictionary in data_sources/drkameleon (an authoring
  dependency, like scripts/import_hsk30_curriculum.py).

No pinyin is guessed for the sentence (example_pinyin stays empty), and a
word that already has an example is never touched. Re-export the curriculum
snapshot afterwards; its import fills empty examples on every database:
    python scripts/seed_vocab_syllabus_examples.py
    python scripts/export_curriculum_snapshot.py
"""
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402

SENTENCE = re.compile(r"^[㐀-鿿，、：；“”‘’！？。]+[。！？]$")
ITEM_SPLIT = re.compile(r"[：:、，,/／；;（）()\s“”\"‘’…⋯—\-+＋A-Za-z0-9]+")
TITLED_READING = re.compile(r"([㐀-鿿]+)\s*[（(]\s*([a-zA-Zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü' ]+)\s*[)）]")


SOURCE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_sources", "drkameleon")
REFERENCE = re.compile(r"^(surname |variant of |old variant of |see |used in |abbr\. for )", re.I)


def norm(pinyin: str | None) -> str:
    return re.sub(r"[\s']", "", pinyin or "").lower()


def polyphones() -> set[str]:
    """Words the source dictionary gives two or more real readings."""
    readings = defaultdict(set)
    for name in sorted(os.listdir(SOURCE_DIR)):
        with open(os.path.join(SOURCE_DIR, name), encoding="utf-8") as f:
            for entry in json.load(f):
                for form in entry["forms"]:
                    if any(not REFERENCE.match(m) for m in form["meanings"]):
                        readings[entry["simplified"]].add(norm(form["transcriptions"]["pinyin"]))
    return {word for word, r in readings.items() if len(r) > 1}


def syllabus_examples(db) -> dict[int, str]:
    """word id -> example sentence, for words without one."""
    level_of = {l.id: l.level for l in db.query(models.HSKLevel)}
    words = db.query(models.VocabularyWord).all()
    vocab = {w.simplified for w in words}
    longest = max(len(v) for v in vocab)
    several = polyphones()
    by_word = defaultdict(list)
    for w in words:
        by_word[w.simplified].append(w)

    def tokens(sentence: str) -> set[str]:
        out, i = set(), 0
        while i < len(sentence):
            for n in range(min(longest, len(sentence) - i), 0, -1):
                if n == 1 or sentence[i:i + n] in vocab:
                    out.add(sentence[i:i + n])
                    i += n
                    break
        return out

    named = defaultdict(list)  # word -> [(level, sentence length, topic id, sentence, titled reading)]
    for g in db.query(models.GrammarTopic).order_by(models.GrammarTopic.id):
        titled = {word: norm(py) for word, py in TITLED_READING.findall(g.title)}
        items = {t for t in ITEM_SPLIT.split(g.title) if t}
        for line in (g.examples or "").split("\n"):
            s = line.strip()
            if not (SENTENCE.match(s) and 4 <= len(s) <= 30):
                continue
            toks = tokens(s)
            for item in items & toks:
                named[item].append((level_of[g.hsk_level_id], len(s), g.id, s, titled.get(item)))

    out = {}
    for w in words:
        if w.example:
            continue
        level = level_of[w.hsk_level_id]
        ambiguous = w.simplified in several
        lower_row = any(level_of[o.hsk_level_id] < level for o in by_word[w.simplified])
        fits = [
            (length, gid, s) for lvl, length, gid, s, titled in named.get(w.simplified, [])
            if (lvl == level if lower_row else lvl <= level)
            and (titled == norm(w.pinyin) if titled else not ambiguous)
        ]
        if fits:
            out[w.id] = min(fits)[2]
    return out


def main() -> None:
    db = SessionLocal()
    found = syllabus_examples(db)
    for word_id, sentence in found.items():
        db.get(models.VocabularyWord, word_id).example = sentence
    db.commit()
    total = db.query(models.VocabularyWord).count()
    have = db.query(models.VocabularyWord).filter(models.VocabularyWord.example.isnot(None)).count()
    print(f"Added {len(found)} syllabus example sentences; {have}/{total} words now have one.")


if __name__ == "__main__":
    main()
