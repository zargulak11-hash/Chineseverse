"""Grammar categories in the learner's language: English names for every
syllabus term (English is the base language, so it had none and showed
the raw Chinese term), Russian from translations, Chinese as is."""

import re

from app import models
from app.database import SessionLocal
from app.services.grammar_terms import CATEGORY_EN
from helpers import expect, register, unique_name

CJK = re.compile(r"[㐀-鿿]")


def test_every_syllabus_category_has_an_english_name(client):
    with SessionLocal() as db:
        cats = {c for (c,) in db.query(models.GrammarTopic.category).distinct() if c}
    assert cats and cats <= set(CATEGORY_EN), sorted(cats - set(CATEGORY_EN))


def test_categories_follow_the_interface_language(client):
    _, h = register(client, unique_name("gram_cat"))
    en = expect(client, "get", "/api/grammar?hsk_level=1", 200, headers={**h, "X-Locale": "en"})
    en_cats = {t["category"] for t in en if t["category"]}
    assert en_cats and not any(CJK.search(c) for c in en_cats), en_cats
    ru = expect(client, "get", "/api/grammar?hsk_level=1", 200, headers={**h, "X-Locale": "ru"})
    assert any(re.search("[а-я]", t["category"] or "") for t in ru)
    zh = expect(client, "get", "/api/grammar?hsk_level=1", 200, headers={**h, "X-Locale": "zh"})
    assert all(CJK.search(t["category"]) for t in zh if t["category"])
    topic = next(t for t in en if t["category"])
    page = expect(client, "get", f"/api/grammar/{topic['id']}", 200, headers={**h, "X-Locale": "en"})
    assert page["category"] == topic["category"]
