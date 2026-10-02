# -*- coding: utf-8 -*-
"""
Fills the missing ru/tg/zh titles of the generated grammar lessons
("HSK3 Grammar 2: 动词") and the summaries of the ones whose summary lists
hand-written grammar points with an English gloss ("是 — to be; 吗 — ...").

Why: those titles were translated for some lessons only -- 35 had no ru/tg
title and 104 no zh title, so a Russian, Tajik or Chinese learner saw
English "Grammar" in the middle of an otherwise localized lesson path.
They are not free text: every one is "HSK{n} Grammar {k}" plus, optionally,
the Chinese category of the official HSK 3.0 syllabus. The translations
already in the database follow one convention ("HSK3 Грамматика 2: 动词"),
and this applies exactly that convention -- the Chinese category is never
translated, it is the syllabus's own term.

The summaries are the lesson's grammar point titles joined by "; ". Each
point that carries an English gloss ("是 — to be") already has a ru/tg title
translation, which is used as is; zh uses the Chinese head ("是") alone. A
point that is an official Chinese syllabus title stays as it is. If any
point has no translation, that summary is left alone (never half-English).

The four hand-written grammar lessons (HSK1 Grammar 1-2, HSK2 Grammar 1,
HSK3 Grammar 1) also get their body translated the same way: each point's
title line uses its existing title translation, and the pattern lines
("不 + verb/adjective") translate only the six grammar terms of PATTERN_TERMS.
Chinese text is never touched, and a body with any line still in English
after that is not translated at all. The trailing "New vocabulary:" list is
kept as it is (practice reads the stored text; learners never see it).

Insert-only: an existing translation (e.g. one an admin edited) is never
touched. Then re-export the curriculum snapshot so every database gets it:
    python scripts/seed_lesson_title_translations.py
    python scripts/export_curriculum_snapshot.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402

TITLE = re.compile(r"^HSK(\d) Grammar (\d+)(?:: (.+))?$")
WORD = {"ru": "Грамматика", "tg": "Грамматика", "zh": "语法"}
COLON = {"ru": ": ", "tg": ": ", "zh": "："}


def localized(title: str, locale: str) -> str | None:
    m = TITLE.match(title)
    if m is None:
        return None
    level, number, category = m.groups()
    text = f"HSK{level} {WORD[locale]} {number}"
    return f"{text}{COLON[locale]}{category}" if category else text


# The only English words in those lessons' pattern lines.
PATTERN_TERMS = {
    "V/Adj": {"ru": "глагол/прилагательное", "tg": "феъл/сифат", "zh": "动词/形容词"},
    "measure word": {"ru": "счётное слово", "tg": "калимаи ченак", "zh": "量词"},
    "small numbers": {"ru": "небольшие числа", "tg": "рақамҳои хурд", "zh": "小数目"},
    "any size": {"ru": "любое число", "tg": "ҳар гуна рақам", "zh": "任何数目"},
    "adjective": {"ru": "прилагательное", "tg": "сифат", "zh": "形容词"},
    "verb": {"ru": "глагол", "tg": "феъл", "zh": "动词"},
}
ENGLISH = re.compile(r"[A-Za-z]{2,}")


def localized_body(content: str, topics: dict[str, int], topic_titles: dict, locale: str) -> str | None:
    body, sep, word_list = content.partition("\nNew vocabulary:")
    lines = body.split("\n")
    if not any(line in topics and " — " in line for line in lines):
        return None
    out = []
    for line in lines:
        if line in topics and " — " in line:
            if locale == "zh":
                line = line.split(" — ")[0]
            elif (topics[line], locale) in topic_titles:
                line = topic_titles[(topics[line], locale)]
            else:
                return None
        else:
            for term, by_locale in PATTERN_TERMS.items():
                line = line.replace(term, by_locale[locale])
        if ENGLISH.search(line.replace("A ", "").replace(" B", "")):
            return None
        out.append(line)
    return "\n".join(out) + sep + word_list


def localized_summary(summary: str, topics: dict[str, int], topic_titles: dict, locale: str) -> str | None:
    parts = [p.strip() for p in summary.split(";")]
    if not any(" — " in p for p in parts) or not all(p in topics for p in parts):
        return None
    out = []
    for p in parts:
        if " — " not in p:
            out.append(p)
        elif locale == "zh":
            out.append(p.split(" — ")[0])
        elif (topics[p], locale) in topic_titles:
            out.append(topic_titles[(topics[p], locale)])
        else:
            return None
    return ("；" if locale == "zh" else "; ").join(out)


def main() -> None:
    db = SessionLocal()
    have = {
        (t.content_key, t.field, t.locale)
        for t in db.query(models.ContentTranslation).filter(
            models.ContentTranslation.content_type == "lesson",
            models.ContentTranslation.field.in_(("title", "summary", "content")),
        )
    }
    topic_titles = {
        (int(t.content_key), t.locale): t.text
        for t in db.query(models.ContentTranslation).filter_by(content_type="grammar_topic", field="title")
    }
    added = 0
    for lesson in db.query(models.Lesson).order_by(models.Lesson.id):
        topics = {g.title: g.id for g in db.query(models.GrammarTopic).filter_by(hsk_level_id=lesson.hsk_level_id)}
        for locale in WORD:
            fields = {
                "title": localized(lesson.title, locale),
                "summary": localized_summary(lesson.summary or "", topics, topic_titles, locale)
                if lesson.lesson_type == "grammar" else None,
                "content": localized_body(lesson.content or "", topics, topic_titles, locale)
                if lesson.lesson_type == "grammar" else None,
            }
            for field, text in fields.items():
                if text is None or (str(lesson.id), field, locale) in have:
                    continue
                db.add(models.ContentTranslation(
                    content_type="lesson", content_key=str(lesson.id), field=field, locale=locale, text=text,
                ))
                added += 1
    db.commit()
    print(f"Added {added} lesson title/summary/content translations.")


if __name__ == "__main__":
    main()
