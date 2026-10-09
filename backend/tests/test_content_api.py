"""Curriculum read APIs: vocabulary, Hanzi and grammar lists filtered by HSK
level -- including HSK 7, 8 and 9 as stages of ONE shared advanced band --
served in the learner's language, and the Hanzi data endpoints."""

import pytest

from app import models
from app.database import SessionLocal
from helpers import expect, register, unique_name

CYRILLIC = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюя")


@pytest.fixture(scope="module")
def h(client):
    return register(client, unique_name("reader"))[1]


def level_ids(db, level):
    return db.query(models.HSKLevel.id).filter_by(level=level).scalar()


@pytest.mark.parametrize("path, model", [
    ("/api/vocab", models.VocabularyWord), ("/api/hanzi", models.Hanzi), ("/api/grammar", models.GrammarTopic),
])
def test_a_level_filter_returns_exactly_that_levels_rows(client, h, path, model):
    with SessionLocal() as db:
        for level in (1, 3):
            want = {r.id for r in db.query(model).filter(model.hsk_level_id == level_ids(db, level))}
            got = {r["id"] for r in expect(client, "get", f"{path}?hsk_level={level}", 200, headers=h)}
            assert got == want and got, (path, level)


@pytest.mark.parametrize("path", ["/api/vocab", "/api/hanzi", "/api/grammar"])
def test_hsk_7_8_9_are_disjoint_stages_of_one_shared_band(client, h, path):
    with SessionLocal() as db:
        band = db.query(models.HSKLevel).filter_by(level=7).one()
        assert band.is_advanced_band
        assert db.query(models.HSKLevel).filter(models.HSKLevel.level.in_((8, 9))).count() == 0
    stages = {lvl: {r["id"] for r in expect(client, "get", f"{path}?hsk_level={lvl}", 200, headers=h)} for lvl in (7, 8, 9)}
    assert all(stages.values()), {k: len(v) for k, v in stages.items()}
    assert not (stages[7] & stages[8] or stages[8] & stages[9] or stages[7] & stages[9])


def ru_meanings(ids):
    with SessionLocal() as db:
        return {int(t.content_key): t.text for t in db.query(models.ContentTranslation).filter(
            models.ContentTranslation.content_type == "vocab_word", models.ContentTranslation.field == "meanings",
            models.ContentTranslation.locale == "ru", models.ContentTranslation.content_key.in_([str(i) for i in ids]))}


def test_meanings_are_served_in_the_learners_language_or_fall_back_to_english(client, h):
    en = {w["id"]: w for w in expect(client, "get", "/api/vocab?hsk_level=1", 200, headers=h)}
    ru = {w["id"]: w for w in expect(client, "get", "/api/vocab?hsk_level=1", 200, headers={**h, "X-Locale": "ru"})}
    assert en.keys() == ru.keys()
    # Chinese and pinyin are never translated.
    assert all(en[i]["simplified"] == ru[i]["simplified"] and en[i]["pinyin"] == ru[i]["pinyin"] for i in en)
    have = ru_meanings(en)
    assert len(have) > 100, len(have)
    for i in en:
        assert ru[i]["meanings"] == have.get(i, en[i]["meanings"]), i
    # An unknown or regional header resolves like the app does.
    regional = expect(client, "get", "/api/vocab?hsk_level=1", 200, headers={**h, "X-Locale": "ru-RU"})
    assert {w["id"]: w["meanings"] for w in regional} == {i: w["meanings"] for i, w in ru.items()}
    unknown = expect(client, "get", "/api/vocab?hsk_level=1", 200, headers={**h, "X-Locale": "xx"})
    assert {w["id"]: w["meanings"] for w in unknown} == {i: w["meanings"] for i, w in en.items()}


def test_curriculum_lists_require_sign_in(client):
    for path in ("/api/vocab?hsk_level=1", "/api/hanzi?hsk_level=1", "/api/grammar?hsk_level=1"):
        expect(client, "get", path, 401)


def test_handwriting_only_lists_the_syllabus_handwriting_characters(client, h):
    every = expect(client, "get", "/api/hanzi", 200, headers=h)
    hand = expect(client, "get", "/api/hanzi?handwriting_only=true", 200, headers=h)
    with SessionLocal() as db:
        want = {r.id for r in db.query(models.Hanzi).filter(models.Hanzi.handwriting_tier.isnot(None))}
    assert {x["id"] for x in hand} == want and 0 < len(hand) < len(every)


def test_stroke_data_is_the_characters_real_strokes(client, h):
    with SessionLocal() as db:
        hz = db.query(models.Hanzi).filter(models.Hanzi.character == "好").first()
        hid, medians = hz.id, hz.stroke_data["medians"]
    data = expect(client, "get", f"/api/hanzi/{hid}/stroke-data", 200, headers=h)
    assert data["character"] == "好" and data["stroke_data"]["medians"] == medians and len(medians) == 6
    expect(client, "get", "/api/hanzi/999999/stroke-data", 404, headers=h)
    expect(client, "get", f"/api/hanzi/{hid}/stroke-data", 401)


def test_example_words_are_real_shortest_first_and_contain_the_character(client, h):
    with SessionLocal() as db:
        hid = db.query(models.Hanzi).filter(models.Hanzi.character == "学").first().id
        real = {w.simplified for w in db.query(models.VocabularyWord).filter(models.VocabularyWord.simplified.contains("学"))}
    ex = expect(client, "get", f"/api/hanzi/{hid}/examples", 200, headers=h)
    words = [w["simplified"] for w in ex]
    assert 1 <= len(words) <= 5 and all("学" in w and w in real for w in words)
    assert [len(w) for w in words] == sorted(len(w) for w in words)
    ru = expect(client, "get", f"/api/hanzi/{hid}/examples", 200, headers={**h, "X-Locale": "ru"})
    assert [w["simplified"] for w in ru] == words
    have = ru_meanings([w["id"] for w in ex])
    assert have, "some example words have a Russian meaning"
    assert [w["meanings"] for w in ru] == [have.get(w["id"], w["meanings"]) for w in ex]
    expect(client, "get", "/api/hanzi/999999/examples", 404, headers=h)


def test_roadmap_shows_every_stage_with_the_new_learner_at_hsk1(client, h):
    road = expect(client, "get", "/api/hsk/roadmap", 200, headers=h)
    assert road["current_level"] == 1
    assert [l["level"] for l in road["levels"]] == list(range(1, 10))
    assert road["levels"][0]["status"] == "current" and all(l["status"] == "locked" for l in road["levels"][1:])
    expect(client, "get", "/api/hsk/roadmap", 401)


@pytest.mark.parametrize("locale", ["ru", "tg", "zh"])
def test_every_companion_is_described_in_the_learners_language(client, locale):
    # Monkey, Koala, Elephant, Cow, Penguin and Owl were translated in
    # scripts/seed_translations.py but never reached the curriculum snapshot,
    # so the onboarding picker showed six English cards in every language.
    english = {a["slug"]: a for a in expect(client, "get", "/api/animals", 200)}
    for a in expect(client, "get", "/api/animals", 200, headers={"X-Locale": locale}):
        for field in ("description", "personality", "tone_style", "special_ability", "preferred_mechanics"):
            assert a[field] != english[a["slug"]][field], (locale, a["slug"], field, a[field])
