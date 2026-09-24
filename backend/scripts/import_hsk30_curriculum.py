# -*- coding: utf-8 -*-
"""
Imports the real, validated HSK 3.0 curriculum (vocabulary, Hanzi, grammar)
built by backend/data_sources/build_*.py into the database.

Idempotent: safe to re-run. Never deletes existing rows or user progress;
only inserts (hsk_level_id, key) pairs that don't already exist, so existing
VocabularyWord/GrammarTopic rows and all UserVocabulary/UserGrammar/UserHanzi
progress are preserved untouched.

Sources (see backend/data_sources/ for raw files + license text):
  - elkmovie/hsk30 (MIT) -- word/character-to-level assignment, exact match
    to the official HSK 3.0 (2021) benchmark counts.
  - drkameleon/complete-hsk-vocabulary (MIT) -- pinyin/meaning/pos/traditional,
    matched onto elkmovie's word list by simplified-form text.
  - skishore/makemeahanzi (dictionary.txt: LGPL v3 / graphics.txt: Arphic
    Public License) -- Hanzi pinyin/definition/radical/decomposition/stroke
    vector data, matched onto elkmovie's character list.
  - krmanik/HSK-3.0 "New HSK (2021)/HSK Grammar" -- official grammar syllabus
    text, parsed into point/category/pattern/examples per level.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app import models

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_sources")

# Real cumulative HSK 3.0 (2021) benchmark totals -- validated exactly against
# elkmovie/hsk30's word/char lists in build_vocab_import.py / build_hanzi_import.py.
REAL_VOCAB_TARGET_CUMULATIVE = {1: 500, 2: 1272, 3: 2245, 4: 3245, 5: 4316, 6: 5456, 7: 11092}
REAL_HANZI_TARGET_CUMULATIVE = {1: 300, 2: 600, 3: 900, 4: 1200, 5: 1500, 6: 1800, 7: 3000}
DIFFICULTY_BAND = {1: "elementary", 2: "elementary", 3: "intermediate",
                    4: "intermediate", 5: "advanced", 6: "advanced", 7: "advanced"}


def load(name):
    return json.load(open(os.path.join(DATA_DIR, name), encoding="utf-8"))


def ensure_hsk_levels(db):
    levels = {l.level: l for l in db.query(models.HSKLevel).all()}
    changed = False
    for lvl_num in range(1, 7):
        lvl = levels.get(lvl_num)
        if lvl is None:
            continue
        target = REAL_VOCAB_TARGET_CUMULATIVE[lvl_num]
        if lvl.total_vocab_target != target:
            print(f"  fixing HSK{lvl_num}.total_vocab_target: {lvl.total_vocab_target} -> {target} (real HSK 3.0 2021 figure)")
            lvl.total_vocab_target = target
            changed = True
    band = levels.get(7)
    if band is None:
        band = models.HSKLevel(
            level=7,
            title="HSK 7-9 (Advanced)",
            description=(
                "Shared advanced vocabulary/Hanzi/grammar pool per the real HSK 3.0 "
                "standard, which treats levels 7, 8 and 9 as one combined advanced "
                "band rather than three independent official word lists."
            ),
            total_vocab_target=REAL_VOCAB_TARGET_CUMULATIVE[7],
            mastery_to_unlock_next=60.0,
            is_advanced_band=True,
        )
        db.add(band)
        print("  created HSKLevel row for the HSK 7-9 advanced band")
        changed = True
    elif not band.is_advanced_band:
        band.is_advanced_band = True
        band.title = band.title or "HSK 7-9 (Advanced)"
        changed = True
    if changed:
        db.commit()
    return {l.level: l for l in db.query(models.HSKLevel).all()}


def import_vocab(db, levels):
    data = load("vocab_import_ready.json")
    existing = {
        (v.hsk_level_id, v.simplified)
        for v in db.query(models.VocabularyWord.hsk_level_id, models.VocabularyWord.simplified)
    }
    inserted = 0
    for lvl_key, entries in data.items():
        lvl = levels[int(lvl_key)]
        for e in entries:
            key = (lvl.id, e["simplified"])
            if key in existing:
                continue
            db.add(models.VocabularyWord(
                hsk_level_id=lvl.id,
                simplified=e["simplified"],
                traditional=e["traditional"],
                pinyin=e["pinyin"],
                meanings=e["meanings"][:300],
                word_type=e["word_type"],
            ))
            existing.add(key)
            inserted += 1
        db.commit()
        print(f"  vocab level {lvl_key}: +{inserted} so far (cumulative)")
    return inserted


def import_hanzi(db, levels):
    data = load("hanzi_import_ready.json")
    existing = {
        (h.hsk_level_id, h.character)
        for h in db.query(models.Hanzi.hsk_level_id, models.Hanzi.character)
    }
    inserted = 0
    for lvl_key, entries in data.items():
        lvl = levels[int(lvl_key)]
        for e in entries:
            key = (lvl.id, e["character"])
            if key in existing:
                continue
            db.add(models.Hanzi(
                hsk_level_id=lvl.id,
                character=e["character"],
                pinyin=e["pinyin"],
                meaning=(e["meaning"] or "")[:300] or None,
                radical=e["radical"],
                decomposition=e["decomposition"],
                stroke_count=e["stroke_count"],
                handwriting_tier=e["handwriting_tier"],
                stroke_data=e["stroke_data"],
            ))
            existing.add(key)
            inserted += 1
        db.commit()
    print(f"  hanzi: +{inserted} inserted")
    return inserted


def import_grammar(db, levels):
    data = load("grammar_import_ready.json")
    existing = {
        (g.hsk_level_id, g.title)
        for g in db.query(models.GrammarTopic.hsk_level_id, models.GrammarTopic.title)
    }
    inserted = 0
    for lvl_key, entries in data.items():
        lvl_num = int(lvl_key)
        lvl = levels[lvl_num]
        for i, e in enumerate(entries):
            key = (lvl.id, e["title"])
            if key in existing:
                continue
            db.add(models.GrammarTopic(
                hsk_level_id=lvl.id,
                title=e["title"][:200],
                pattern=(e["pattern"] or "")[:200] or None,
                explanation=None,  # source syllabus has no authored prose explanation (see report)
                examples=e["examples"] or None,
                category=e["category"],
                difficulty=DIFFICULTY_BAND[lvl_num],
                order_index=i,
            ))
            existing.add(key)
            inserted += 1
        db.commit()
    print(f"  grammar: +{inserted} inserted")
    return inserted


if __name__ == "__main__":
    db = SessionLocal()
    print("Ensuring HSK level rows (1-6 targets fixed to real HSK 3.0 figures, 7-9 band created)...")
    levels = ensure_hsk_levels(db)

    print("Importing vocabulary...")
    v = import_vocab(db, levels)

    print("Importing Hanzi...")
    h = import_hanzi(db, levels)

    print("Importing grammar...")
    g = import_grammar(db, levels)

    print(f"\nDone. Inserted: {v} vocabulary words, {h} hanzi, {g} grammar topics.")

    print("\n=== FINAL DB COUNTS ===")
    from sqlalchemy import func
    for lvl in db.query(models.HSKLevel).order_by(models.HSKLevel.level).all():
        vc = db.query(models.VocabularyWord).filter_by(hsk_level_id=lvl.id).count()
        hc = db.query(models.Hanzi).filter_by(hsk_level_id=lvl.id).count()
        gc = db.query(models.GrammarTopic).filter_by(hsk_level_id=lvl.id).count()
        print(f"HSK{lvl.level} (id={lvl.id}, advanced_band={lvl.is_advanced_band}): vocab={vc} hanzi={hc} grammar={gc}")
    db.close()
