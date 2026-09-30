# -*- coding: utf-8 -*-
"""
Exports the curated curriculum content of the database this runs against
(vocabulary, grammar, lessons, and every ContentTranslation row) into
app/seed_content/curriculum.json.gz, which app.services.curriculum imports
idempotently on every startup.

Why: the full HSK 3.0 vocabulary/grammar, the generated HSK1-9 lessons and
the ru/tg/zh translations were only ever loaded into one developer database
by hand (scripts/import_hsk30_curriculum.py, generate_hsk_lessons.py,
seed_*translations.py -- the first reads gitignored files, the translation
scripts are keyed by that database's row ids). A deployed server only runs
migrations + seed_all, so it had a fraction of the curriculum.

Every row is written with a NATURAL key (HSK level + word, slug, code, ...)
instead of its id, because ids differ between databases (the dev DB's HSK1
row is id 13; a fresh database's is id 1). Content only -- never user data.

Run from backend/:  python scripts/export_curriculum_snapshot.py
"""
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.services.curriculum import SNAPSHOT_PATH  # noqa: E402


def main() -> None:
    db = SessionLocal()
    level_of = {l.id: l.level for l in db.query(models.HSKLevel)}

    vocab = [
        {
            "level": level_of[w.hsk_level_id], "simplified": w.simplified,
            "traditional": w.traditional, "pinyin": w.pinyin, "meanings": w.meanings,
            "word_type": w.word_type, "example": w.example, "example_pinyin": w.example_pinyin,
        }
        for w in db.query(models.VocabularyWord).order_by(models.VocabularyWord.id)
    ]
    grammar = [
        {
            "level": level_of[g.hsk_level_id], "title": g.title, "pattern": g.pattern,
            "explanation": g.explanation, "examples": g.examples, "category": g.category,
            "difficulty": g.difficulty, "order_index": g.order_index,
        }
        for g in db.query(models.GrammarTopic).order_by(models.GrammarTopic.id)
    ]
    lessons = [
        {
            "level": level_of.get(l.hsk_level_id), "title": l.title, "summary": l.summary,
            "content": l.content, "lesson_type": l.lesson_type, "order_index": l.order_index,
            "skills": sorted(s.code for s in l.skills),
        }
        for l in db.query(models.Lesson).order_by(models.Lesson.id)
    ]

    # id -> natural key, per translated content type
    keys: dict[str, dict[str, str]] = {
        "vocab_word": {str(w.id): f"{level_of[w.hsk_level_id]}|{w.simplified}" for w in db.query(models.VocabularyWord)},
        "grammar_topic": {str(g.id): f"{level_of[g.hsk_level_id]}|{g.title}" for g in db.query(models.GrammarTopic)},
        "lesson": {str(l.id): f"{level_of.get(l.hsk_level_id)}|{l.title}" for l in db.query(models.Lesson)},
        "hanzi": {str(h.id): f"{level_of[h.hsk_level_id]}|{h.character}" for h in db.query(models.Hanzi)},
        "hsk_level": {str(l.id): str(l.level) for l in db.query(models.HSKLevel)},
        "animal": {str(a.id): a.slug for a in db.query(models.Animal)},
        "skill": {str(s.id): s.code for s in db.query(models.Skill)},
        "achievement": {str(a.id): a.code for a in db.query(models.Achievement)},
        "location": {str(x.id): x.slug for x in db.query(models.Location)},
        "scenario": {str(x.id): x.slug for x in db.query(models.Scenario)},
        "mission": {str(x.id): x.slug for x in db.query(models.Mission)},
        "npc": {str(n.id): f"{n.location.slug}|{n.name}" for n in db.query(models.NPC)},
        "dialogue": {
            str(d.id): f"{d.scenario.slug if d.scenario else ''}|{d.turn_index}|{d.speaker}"
            for d in db.query(models.Dialogue)
        },
        "pet_teacher_case": {str(c.id): c.wrong_sentence for c in db.query(models.PetTeacherCase)},
    }
    keys["dialogue_choice"] = {
        str(c.id): f"{keys['dialogue'][str(c.dialogue_id)]}|{c.label}" for c in db.query(models.DialogueChoice)
    }
    # Types keyed by a stable code already (quest_template, ui_string) pass through.
    translations, skipped = [], 0
    for t in db.query(models.ContentTranslation).order_by(models.ContentTranslation.id):
        mapping = keys.get(t.content_type)
        natural = mapping.get(t.content_key) if mapping is not None else t.content_key
        if natural is None:
            skipped += 1  # translation of a row that no longer exists
            continue
        translations.append([t.content_type, natural, t.field, t.locale, t.text])

    snapshot = {"version": 1, "vocab": vocab, "grammar": grammar, "lessons": lessons, "translations": translations}
    os.makedirs(os.path.dirname(SNAPSHOT_PATH), exist_ok=True)
    with gzip.open(SNAPSHOT_PATH, "wt", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, separators=(",", ":"))
    print(
        f"Wrote {SNAPSHOT_PATH}: {len(vocab)} vocab, {len(grammar)} grammar, {len(lessons)} lessons, "
        f"{len(translations)} translations ({skipped} orphaned translations skipped)."
    )
    db.close()


if __name__ == "__main__":
    main()
