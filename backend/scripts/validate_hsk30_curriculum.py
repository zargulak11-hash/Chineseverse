# -*- coding: utf-8 -*-
"""
Data-integrity validation for the HSK 3.0 curriculum: duplicate Hanzi/
vocabulary/grammar, missing pinyin/meanings, invalid HSK level assignments,
broken relationships, and roadmap-vs-list count consistency. Read-only.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func
from app.database import SessionLocal
from app import models

db = SessionLocal()
problems = []


def report(name, count, sample=None):
    status = "OK" if count == 0 else f"FOUND {count}"
    print(f"[{'PASS' if count == 0 else 'FAIL'}] {name}: {status}" + (f"  e.g. {sample}" if sample else ""))
    if count:
        problems.append(name)


# 1. Duplicate vocabulary within a level
dupe_vocab = (
    db.query(models.VocabularyWord.hsk_level_id, models.VocabularyWord.simplified, func.count())
    .group_by(models.VocabularyWord.hsk_level_id, models.VocabularyWord.simplified)
    .having(func.count() > 1)
    .all()
)
report("duplicate vocabulary words within a level", len(dupe_vocab), dupe_vocab[:3])

# 2. Duplicate Hanzi within a level
dupe_hanzi = (
    db.query(models.Hanzi.hsk_level_id, models.Hanzi.character, func.count())
    .group_by(models.Hanzi.hsk_level_id, models.Hanzi.character)
    .having(func.count() > 1)
    .all()
)
report("duplicate Hanzi within a level", len(dupe_hanzi), dupe_hanzi[:3])

# 3. Duplicate grammar topics within a level (by title)
dupe_grammar = (
    db.query(models.GrammarTopic.hsk_level_id, models.GrammarTopic.title, func.count())
    .group_by(models.GrammarTopic.hsk_level_id, models.GrammarTopic.title)
    .having(func.count() > 1)
    .all()
)
report("duplicate grammar topics within a level", len(dupe_grammar), dupe_grammar[:3])

# 4. Vocabulary missing pinyin or meanings
missing_vocab = (
    db.query(models.VocabularyWord)
    .filter((models.VocabularyWord.pinyin.is_(None)) | (models.VocabularyWord.pinyin == "") |
            (models.VocabularyWord.meanings.is_(None)) | (models.VocabularyWord.meanings == ""))
    .count()
)
report("vocabulary rows missing pinyin/meanings", missing_vocab)

# 5. Hanzi missing pinyin or meaning
missing_hanzi = (
    db.query(models.Hanzi)
    .filter((models.Hanzi.pinyin.is_(None)) | (models.Hanzi.pinyin == "") |
            (models.Hanzi.meaning.is_(None)) | (models.Hanzi.meaning == ""))
    .count()
)
report("hanzi rows missing pinyin/meaning", missing_hanzi)

# 6. Grammar missing title or pattern
missing_grammar = (
    db.query(models.GrammarTopic)
    .filter((models.GrammarTopic.title.is_(None)) | (models.GrammarTopic.title == ""))
    .count()
)
report("grammar rows missing a title", missing_grammar)

# 7. Orphaned FK references (hsk_level_id pointing nowhere)
valid_level_ids = {l.id for l in db.query(models.HSKLevel.id).all()}
orphan_vocab = db.query(models.VocabularyWord).filter(~models.VocabularyWord.hsk_level_id.in_(valid_level_ids)).count()
orphan_hanzi = db.query(models.Hanzi).filter(~models.Hanzi.hsk_level_id.in_(valid_level_ids)).count()
orphan_grammar = db.query(models.GrammarTopic).filter(~models.GrammarTopic.hsk_level_id.in_(valid_level_ids)).count()
report("vocabulary with invalid hsk_level_id", orphan_vocab)
report("hanzi with invalid hsk_level_id", orphan_hanzi)
report("grammar with invalid hsk_level_id", orphan_grammar)

# 8. HSKLevel sanity: exactly one advanced_band row, levels 1-7 present, no duplicate level numbers
levels = db.query(models.HSKLevel).order_by(models.HSKLevel.level).all()
level_numbers = [l.level for l in levels]
report("duplicate HSKLevel.level numbers", len(level_numbers) - len(set(level_numbers)))
band_rows = [l for l in levels if l.is_advanced_band]
report("HSKLevel rows with is_advanced_band=True (expect exactly 1)", 0 if len(band_rows) == 1 else 1, [b.level for b in band_rows])
report("HSK 1-6 present as real (non-advanced) levels", 0 if set(range(1, 7)).issubset(set(level_numbers)) else 1)

# 9. Handwriting tier values are only the 3 real tiers or null
bad_tier = db.query(models.Hanzi).filter(
    models.Hanzi.handwriting_tier.isnot(None),
    ~models.Hanzi.handwriting_tier.in_(["elementary", "intermediate", "advanced"]),
).count()
report("hanzi with an invalid handwriting_tier value", bad_tier)

# 10. No fabricated "placeholder" grammar titles (spot-check for known fake patterns)
placeholder_titles = (
    db.query(models.GrammarTopic)
    .filter(models.GrammarTopic.title.ilike("%placeholder%") | models.GrammarTopic.title.ilike("%grammar 4%") | models.GrammarTopic.title.ilike("%advanced grammar%"))
    .all()
)
report("grammar topics with placeholder-looking titles", len(placeholder_titles), [t.title for t in placeholder_titles[:3]])

print("\n=== CUMULATIVE COUNTS vs validated HSK 3.0 benchmark ===")
BENCH_VOCAB = {1: 500, 2: 1272, 3: 2245, 4: 3245, 5: 4316, 6: 5456, 7: 11092}
BENCH_HANZI = {1: 300, 2: 600, 3: 900, 4: 1200, 5: 1500, 6: 1800, 7: 3000}
cum_v, cum_h = 0, 0
for lvl in levels:
    v = db.query(models.VocabularyWord).filter(models.VocabularyWord.hsk_level_id.in_([l.id for l in levels if l.level <= lvl.level])).count()
    h = db.query(models.Hanzi).filter(models.Hanzi.hsk_level_id.in_([l.id for l in levels if l.level <= lvl.level])).count()
    bv, bh = BENCH_VOCAB.get(lvl.level), BENCH_HANZI.get(lvl.level)
    print(f"HSK{lvl.level}: vocab_cumulative={v} (benchmark {bv}, diff {v-bv if bv else 'n/a'})  hanzi_cumulative={h} (benchmark {bh}, diff {h-bh if bh else 'n/a'})")

print(f"\n{'ALL CHECKS PASSED' if not problems else f'{len(problems)} CHECK(S) FAILED: ' + ', '.join(problems)}")
db.close()
