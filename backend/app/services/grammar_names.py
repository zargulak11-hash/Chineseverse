"""What a grammar point is called in the learner's language.

572 of the syllabus points are titled in Chinese grammar terminology
(方位名词：上、下……, 主谓句1：动词谓语句) -- metalanguage, not the Chinese
being taught -- so a Russian or Tajik screen showed them as Chinese. Those
titles have a "name" ContentTranslation (ru/tg) and an English name in
seed_content/grammar_names_en.json; a Chinese interface keeps the title.
Titles that *are* the pattern being taught (从, 越⋯⋯越⋯⋯) have no name.
"""

from __future__ import annotations

import json
import os

from sqlalchemy.orm import Session

from app import models
from app.services.localization import load_translations, tr

_EN_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "seed_content", "grammar_names_en.json")
_EN_NAMES: dict[str, str] | None = None


def _en_names() -> dict[str, str]:
    """Keyed "level|title": a title like 用反问句表示强调 recurs across levels.
    English is never a ContentTranslation row (it is what the others fall
    back to), so it is a static file."""
    global _EN_NAMES
    if _EN_NAMES is None:
        with open(_EN_PATH, encoding="utf-8") as f:
            _EN_NAMES = json.load(f)
    return _EN_NAMES


def syllabus_names(db: Session, topics, locale: str) -> dict[int, str]:
    """{topic id: name} for the points titled in Chinese grammar terms."""
    topics = list(topics)
    if locale == "zh" or not topics:
        return {}
    if locale in ("ru", "tg"):
        trs = load_translations(db, "grammar_topic", [str(t.id) for t in topics], locale)
        return {t.id: trs[str(t.id)]["name"] for t in topics if "name" in trs.get(str(t.id), {})}
    levels = dict(db.query(models.HSKLevel.id, models.HSKLevel.level))
    en = _en_names()
    return {t.id: en[k] for t in topics if (k := f"{levels.get(t.hsk_level_id)}|{t.title}") in en}


def titles(db: Session, topics, locale: str) -> dict[int, str]:
    """{topic id: title to show}: the syllabus name, else the translated
    title, else the title itself."""
    topics = list(topics)
    named = syllabus_names(db, topics, locale)
    trs = load_translations(db, "grammar_topic", [str(t.id) for t in topics], locale)
    return {t.id: named.get(t.id) or tr(trs, t.id, "title", t.title) for t in topics}
