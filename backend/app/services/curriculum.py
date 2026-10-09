"""Idempotent import of the committed curriculum snapshot.

app/seed_content/curriculum.json.gz (written by
scripts/export_curriculum_snapshot.py) carries the full HSK 3.0 vocabulary
and grammar, the HSK1-9 lessons and all ru/tg/zh content translations,
every row identified by a natural key rather than a database id. Running
this on startup makes any database -- a fresh clone, CI, production --
reach the same curriculum as the one it was exported from.

Insert-only by design: existing content rows and translations are never
overwritten or deleted (an admin may have edited them), and user progress
tables are never touched. The one exception is filling a vocabulary
example that is still empty.
"""

from __future__ import annotations

import gzip
import json
import logging
import os

from sqlalchemy.orm import Session

from app import models

logger = logging.getLogger(__name__)

SNAPSHOT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seed_content", "curriculum.json.gz"
)


def _natural_key_index(db: Session, level_of: dict[int, int]) -> dict[str, dict[str, int]]:
    """natural key -> id on THIS database, per translated content type."""
    idx: dict[str, dict[str, int]] = {
        "vocab_word": {f"{level_of[w.hsk_level_id]}|{w.simplified}": w.id for w in db.query(models.VocabularyWord)},
        "grammar_topic": {f"{level_of[g.hsk_level_id]}|{g.title}": g.id for g in db.query(models.GrammarTopic)},
        "lesson": {f"{level_of.get(l.hsk_level_id)}|{l.title}": l.id for l in db.query(models.Lesson)},
        "hanzi": {f"{level_of[h.hsk_level_id]}|{h.character}": h.id for h in db.query(models.Hanzi)},
        "hsk_level": {str(level): lid for lid, level in level_of.items()},
        "animal": {a.slug: a.id for a in db.query(models.Animal)},
        "skill": {s.code: s.id for s in db.query(models.Skill)},
        "achievement": {a.code: a.id for a in db.query(models.Achievement)},
        "location": {x.slug: x.id for x in db.query(models.Location)},
        "scenario": {x.slug: x.id for x in db.query(models.Scenario)},
        "mission": {x.slug: x.id for x in db.query(models.Mission)},
        "npc": {f"{n.location.slug}|{n.name}": n.id for n in db.query(models.NPC)},
        "pet_teacher_case": {c.wrong_sentence: c.id for c in db.query(models.PetTeacherCase)},
    }
    # Plain column queries, not relationships: rows seeded earlier in this
    # same session may not have their relationship attributes populated.
    scenario_slug = dict(db.query(models.Scenario.id, models.Scenario.slug))
    dialogue_key = {
        d_id: f"{scenario_slug.get(s_id, '')}|{turn}|{speaker}"
        for d_id, s_id, turn, speaker in db.query(
            models.Dialogue.id, models.Dialogue.scenario_id, models.Dialogue.turn_index, models.Dialogue.speaker
        )
    }
    idx["dialogue"] = {k: i for i, k in dialogue_key.items()}
    idx["dialogue_choice"] = {
        f"{dialogue_key.get(d_id)}|{label}": c_id
        for c_id, d_id, label in db.query(models.DialogueChoice.id, models.DialogueChoice.dialogue_id, models.DialogueChoice.label)
    }
    return idx


def import_curriculum(db: Session, path: str = SNAPSHOT_PATH) -> dict[str, int]:
    if not os.path.exists(path):
        logger.warning("Curriculum snapshot %s not found; skipping curriculum import.", path)
        return {}
    with gzip.open(path, "rt", encoding="utf-8") as f:
        snap = json.load(f)

    db.flush()
    level_rows = {l.level: l.id for l in db.query(models.HSKLevel)}
    level_of = {lid: level for level, lid in level_rows.items()}
    counts = {"vocab": 0, "examples": 0, "grammar": 0, "lessons": 0, "translations": 0}

    words = {(w.hsk_level_id, w.simplified): w for w in db.query(models.VocabularyWord)}
    for v in snap["vocab"]:
        level_id = level_rows.get(v["level"])
        if level_id is None:
            continue
        existing = words.get((level_id, v["simplified"]))
        if existing is None:
            db.add(models.VocabularyWord(
                hsk_level_id=level_id, simplified=v["simplified"], traditional=v["traditional"],
                pinyin=v["pinyin"], meanings=v["meanings"], word_type=v["word_type"],
                example=v["example"], example_pinyin=v["example_pinyin"],
            ))
            counts["vocab"] += 1
        elif not existing.example and v["example"]:
            existing.example, existing.example_pinyin = v["example"], v["example_pinyin"]
            counts["examples"] += 1

    topics = {(g.hsk_level_id, g.title) for g in db.query(models.GrammarTopic.hsk_level_id, models.GrammarTopic.title)}
    for g in snap["grammar"]:
        level_id = level_rows.get(g["level"])
        if level_id is None or (level_id, g["title"]) in topics:
            continue
        db.add(models.GrammarTopic(
            hsk_level_id=level_id, title=g["title"], pattern=g["pattern"], explanation=g["explanation"],
            examples=g["examples"], category=g["category"], difficulty=g["difficulty"],
            order_index=g["order_index"],
        ))
        topics.add((level_id, g["title"]))
        counts["grammar"] += 1

    skills = {s.code: s for s in db.query(models.Skill)}
    lessons = {(l.hsk_level_id, l.title) for l in db.query(models.Lesson.hsk_level_id, models.Lesson.title)}
    for l in snap["lessons"]:
        level_id = level_rows.get(l["level"]) if l["level"] is not None else None
        if (level_id, l["title"]) in lessons:
            continue
        lesson = models.Lesson(
            hsk_level_id=level_id, title=l["title"], summary=l["summary"], content=l["content"],
            lesson_type=l["lesson_type"], order_index=l["order_index"],
        )
        lesson.skills = [skills[c] for c in l["skills"] if c in skills]
        db.add(lesson)
        lessons.add((level_id, l["title"]))
        counts["lessons"] += 1

    db.flush()
    idx = _natural_key_index(db, level_of)
    have = {
        (t.content_type, t.content_key, t.field, t.locale)
        for t in db.query(
            models.ContentTranslation.content_type, models.ContentTranslation.content_key,
            models.ContentTranslation.field, models.ContentTranslation.locale,
        )
    }
    # Rows are [type, natural key, field, locale, text] or, for a draft
    # awaiting native review, the same plus a 6th element "draft".
    for content_type, natural, field, locale, text, *rest in snap["translations"]:
        source = rest[0] if rest else None
        mapping = idx.get(content_type)
        if mapping is None:
            key = natural  # already a stable code (quest_template, ui_string)
        else:
            row_id = mapping.get(natural)
            if row_id is None:
                continue
            key = str(row_id)
        if (content_type, key, field, locale) in have:
            continue
        db.add(models.ContentTranslation(
            content_type=content_type, content_key=key, field=field, locale=locale, text=text, source=source,
        ))
        have.add((content_type, key, field, locale))
        counts["translations"] += 1

    if any(counts.values()):
        logger.info("Curriculum snapshot imported: %s", counts)
    return counts
