"""List the content translations still marked "draft" for a native speaker.

Usage (from backend/):
    python scripts/export_translation_review.py [locale ...] > review.csv

Writes CSV to stdout: locale, HSK level, content type, field, the Chinese
item (word / character / title), its pinyin, the English original and the
draft translation. A reviewer corrects the draft in the admin tools; an
edited translation should have its `source` cleared so it drops off this
list. With no locales given, all of ru, tg and zh are listed (Tajik first:
it needs review most).
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402

ORIGINALS = {
    # content type -> (model, Chinese column, pinyin column, {field: English column})
    "vocab_word": (models.VocabularyWord, "simplified", "pinyin", {"meanings": "meanings"}),
    "hanzi": (models.Hanzi, "character", "pinyin", {"meaning": "meaning"}),
    "grammar_topic": (models.GrammarTopic, "title", None, {"title": "title", "explanation": "explanation",
                                                           "category": "category", "difficulty": "difficulty"}),
    "lesson": (models.Lesson, "title", None, {"title": "title", "summary": "summary", "content": "content"}),
    "achievement": (models.Achievement, "code", None, {"title": "title", "description": "description"}),
}


def main(locales):
    db = SessionLocal()
    level_of = dict(db.query(models.HSKLevel.id, models.HSKLevel.level))
    out = csv.writer(sys.stdout, lineterminator="\n")
    out.writerow(["locale", "hsk", "type", "field", "item", "pinyin", "english", "draft"])
    order = {"tg": 0, "ru": 1, "zh": 2}
    rows = (
        db.query(models.ContentTranslation)
        .filter(models.ContentTranslation.source == "draft", models.ContentTranslation.locale.in_(locales))
        .all()
    )
    rows.sort(key=lambda t: (order.get(t.locale, 9), t.content_type, int(t.content_key) if t.content_key.isdigit() else 0))
    for t in rows:
        spec = ORIGINALS.get(t.content_type)
        row = db.get(spec[0], int(t.content_key)) if spec and t.content_key.isdigit() else None
        level = level_of.get(getattr(row, "hsk_level_id", None), "") if row is not None else ""
        item = getattr(row, spec[1], "") if row is not None else t.content_key
        pinyin = getattr(row, spec[2], "") if row is not None and spec[2] else ""
        english = getattr(row, spec[3].get(t.field, ""), "") if row is not None else ""
        out.writerow([t.locale, level, t.content_type, t.field, item, pinyin, english, t.text])


if __name__ == "__main__":
    main(sys.argv[1:] or ["tg", "ru", "zh"])
