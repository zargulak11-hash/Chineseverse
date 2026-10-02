# -*- coding: utf-8 -*-
"""ru / tg meanings reused from translations that already exist -- never
newly written.

The project has no Russian or Tajik dictionary source; every ru/tg meaning
in the database was written for a specific row. Two cases can still reuse
one safely, because the text would mean exactly the same thing:

- a vocabulary row without ru/tg, when the SAME word at another HSK level
  has them AND both rows have the same reading and the same first English
  sense (白 bái "white" at HSK 1 takes HSK 2's "белый"; HSK 3's 白 bái "in
  vain" does not);
- a Hanzi without ru/tg, when the single-character vocabulary word with the
  same character and reading has them AND the character's first English
  sense is one of that word's senses (才 "ability, talent" takes 才's
  "талант, способность"; 带 "belt, strap" does not take 带's "нести").

Insert-only (an existing translation is never touched). Re-export the
curriculum snapshot afterwards:
    python scripts/seed_reuse_translations.py
    python scripts/export_curriculum_snapshot.py
"""
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402

LOCALES = ("ru", "tg")


def norm(pinyin: str | None) -> str:
    return re.sub(r"[\s']", "", pinyin or "").lower()


def senses(text: str | None) -> list[str]:
    return [s.strip().lower() for s in re.split(r"[;,]", text or "") if s.strip()]


def plan(db) -> tuple[list[tuple], list[tuple]]:
    """([(word, donor word)], [(hanzi, donor word)]) to copy ru/tg from."""
    words = db.query(models.VocabularyWord).all()
    have = defaultdict(dict)
    for t in db.query(models.ContentTranslation).filter_by(content_type="vocab_word", field="meanings"):
        have[int(t.content_key)][t.locale] = t.text
    complete = {w.id for w in words if all(loc in have[w.id] for loc in LOCALES)}

    by_sense = defaultdict(list)
    for w in words:
        if w.id in complete:
            by_sense[(w.simplified, norm(w.pinyin), (senses(w.meanings) or [""])[0])].append(w)
    vocab = []
    for w in words:
        if any(loc in have[w.id] for loc in LOCALES):
            continue
        donors = by_sense.get((w.simplified, norm(w.pinyin), (senses(w.meanings) or [""])[0]))
        if donors:
            vocab.append((w, min(donors, key=lambda d: d.id)))

    hanzi_have = defaultdict(set)
    for t in db.query(models.ContentTranslation).filter_by(content_type="hanzi", field="meaning"):
        hanzi_have[int(t.content_key)].add(t.locale)
    single = defaultdict(list)
    for w in words:
        if len(w.simplified) == 1 and w.id in complete:
            single[(w.simplified, norm(w.pinyin))].append(w)
    hanzi = []
    for h in db.query(models.Hanzi):
        if hanzi_have[h.id]:
            continue
        first = (senses(h.meaning) or [None])[0]
        donors = [w for w in single.get((h.character, norm(h.pinyin)), []) if first in senses(w.meanings)]
        if donors:
            hanzi.append((h, min(donors, key=lambda d: d.id)))
    return vocab, hanzi


def main() -> None:
    db = SessionLocal()
    vocab, hanzi = plan(db)
    text = defaultdict(dict)
    for t in db.query(models.ContentTranslation).filter_by(content_type="vocab_word", field="meanings"):
        text[int(t.content_key)][t.locale] = t.text
    added = 0
    for content_type, field, pairs in (("vocab_word", "meanings", vocab), ("hanzi", "meaning", hanzi)):
        for row, donor in pairs:
            for loc in LOCALES:
                db.add(models.ContentTranslation(
                    content_type=content_type, content_key=str(row.id), field=field, locale=loc,
                    text=text[donor.id][loc],
                ))
                added += 1
    db.commit()
    print(f"Reused {added} ru/tg meanings: {len(vocab)} vocabulary words, {len(hanzi)} Hanzi.")


if __name__ == "__main__":
    main()
