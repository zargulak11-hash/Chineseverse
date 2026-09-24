# -*- coding: utf-8 -*-
"""
Generates structured lessons for HSK1-9 from real GrammarTopic/VocabularyWord
data, closing the gap where most levels had far too few Lesson rows to
represent a meaningful learning path (HSK1 had 5 hand-authored lessons
covering a handful of the level's 60 real grammar points, HSK2 had 2
covering a handful of 89; HSK3-9 had zero). The hand-authored lessons from
seed_learning.py are left in place untouched -- this only adds more real,
chunked chapters alongside them, covering the rest of each level's grammar.

Every fact in a generated lesson is copied verbatim from an already-imported,
already-validated GrammarTopic/VocabularyWord row -- title, pattern, and
examples come straight from the real HSK 3.0 syllabus text (krmanik/HSK-3.0),
and vocabulary entries come straight from the real merged vocabulary import.
Nothing here is newly authored prose or an invented example sentence; this
script only curates/chunks real rows into lesson-sized reading chapters.

Idempotent: skips any title that already exists.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app import models

CHUNK_SIZE = 6
VOCAB_PER_LESSON = 8


def build_lessons_for_level(db, level_row, display_level, vocab_ids=None, grammar_ids=None):
    grammar_q = db.query(models.GrammarTopic).filter(models.GrammarTopic.hsk_level_id == level_row.id)
    if grammar_ids is not None:
        grammar_q = grammar_q.filter(models.GrammarTopic.id.in_(grammar_ids or [0]))
    topics = grammar_q.order_by(models.GrammarTopic.id).all()

    vocab_q = db.query(models.VocabularyWord).filter(models.VocabularyWord.hsk_level_id == level_row.id)
    if vocab_ids is not None:
        vocab_q = vocab_q.filter(models.VocabularyWord.id.in_(vocab_ids or [0]))
    words = vocab_q.order_by(models.VocabularyWord.id).all()

    chunks = [topics[i:i + CHUNK_SIZE] for i in range(0, len(topics), CHUNK_SIZE)]
    created = 0
    for idx, chunk in enumerate(chunks, start=1):
        # Deterministic tie-break: most frequent category in the chunk, then
        # alphabetically first -- `set()` iteration order is randomized per
        # process (PYTHONHASHSEED), so without a stable tie-break this could
        # pick a different category label (hence a different title) on a
        # re-run and defeat the title-based idempotency check below.
        categories = [t.category for t in chunk if t.category]
        rep_category = min(set(categories), key=lambda c: (-categories.count(c), c)) if categories else None
        title = f"HSK{display_level} Grammar {idx}" + (f": {rep_category}" if rep_category else "")
        title = title[:200]

        summary = "; ".join(t.title for t in chunk)[:300]

        content_parts = []
        for t in chunk:
            block = t.title
            if t.pattern and t.pattern != t.title:
                block += f"\n{t.pattern}"
            if t.examples:
                block += f"\n{t.examples}"
            content_parts.append(block)

        vocab_slice = words[(idx - 1) * VOCAB_PER_LESSON: idx * VOCAB_PER_LESSON]
        if vocab_slice:
            vocab_lines = [f"{w.simplified} ({w.pinyin}) = {w.meanings}" for w in vocab_slice]
            content_parts.append("New vocabulary:\n" + "\n".join(vocab_lines))

        content = "\n\n".join(content_parts)[:8000]

        existing = db.query(models.Lesson).filter_by(title=title).first()
        if existing:
            continue
        lesson = models.Lesson(
            hsk_level_id=level_row.id, title=title, summary=summary,
            content=content, lesson_type="grammar", order_index=idx,
        )
        db.add(lesson)
        db.flush()
        for code in ("grammar", "vocabulary"):
            skill = db.query(models.Skill).filter_by(code=code).first()
            if skill and skill not in lesson.skills:
                lesson.skills.append(skill)
        created += 1
    return created


if __name__ == "__main__":
    db = SessionLocal()
    levels = {l.level: l for l in db.query(models.HSKLevel).all()}
    total = 0

    for lvl_num in (1, 2, 3, 4, 5, 6):
        lvl = levels[lvl_num]
        n = build_lessons_for_level(db, lvl, lvl_num)
        db.commit()
        print(f"HSK{lvl_num}: +{n} lessons")
        total += n

    # HSK 7-9 band: split into the same 3 real thirds used everywhere else,
    # so lessons for "HSK 8" are drawn from the real middle third of the
    # shared pool, not a duplicate of HSK 7's or HSK 9's.
    band = levels[7]
    from app.services.hsk_band import split_thirds
    grammar_ids_all = [g.id for g in db.query(models.GrammarTopic.id).filter_by(hsk_level_id=band.id).order_by(models.GrammarTopic.id).all()]
    vocab_ids_all = [v.id for v in db.query(models.VocabularyWord.id).filter_by(hsk_level_id=band.id).order_by(models.VocabularyWord.id).all()]
    g_thirds = split_thirds(grammar_ids_all)
    v_thirds = split_thirds(vocab_ids_all)
    for i, stage in enumerate((7, 8, 9)):
        n = build_lessons_for_level(db, band, stage, vocab_ids=v_thirds[i], grammar_ids=g_thirds[i])
        db.commit()
        print(f"HSK{stage} (advanced band stage): +{n} lessons")
        total += n

    print(f"\nTotal new lessons created: {total}")

    print("\n=== FINAL LESSON COUNTS PER LEVEL ===")
    for lvl in db.query(models.HSKLevel).order_by(models.HSKLevel.level).all():
        c = db.query(models.Lesson).filter_by(hsk_level_id=lvl.id).count()
        print(f"HSK{lvl.level}: {c} lessons")
    db.close()
