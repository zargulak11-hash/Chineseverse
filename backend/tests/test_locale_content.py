"""The selected language decides the supporting text a learner reads --
translations, explanations, feedback -- while Chinese learning material stays
Chinese. These cover the places that used to mix languages: a Chinese UI was
handed English translations of Chinese lines, and text stored during a round
(a mistake's question) kept the language of that round."""

import re

import pytest

from app import models
from app.database import SessionLocal
from app.services.internet_content import ITEMS
from helpers import expect, register, unique_name

LATIN_WORDS = re.compile(r"\b[A-Za-z]{3,}\b")


@pytest.fixture(scope="module")
def zh(client):
    _, h = register(client, unique_name("zhui"))
    return {**h, "X-Locale": "zh"}


def test_a_chinese_ui_gets_no_english_translation_of_a_chinese_line(client, zh):
    d = expect(client, "get", "/api/detective/files/the-teachers-cup", 200, headers=zh)
    lines = d["brief"] + d["evidence"] + d["timeline"] + [s["statement"] for s in d["suspects"]]
    assert lines and all(l["tr"] is None for l in lines), [l["tr"] for l in lines if l["tr"]]


def test_a_chinese_ui_listens_for_the_chinese_line_not_its_english_meaning(client, zh):
    s = expect(client, "post", "/api/practice/sessions", 201, headers=zh, json={"source": "scene", "scene": "restaurant"})
    for q in s["questions"]:
        assert not (q["prompt"].get("translation") or "").strip(), q["prompt"]
        if q["type"] == "scene_listen":  # options are the lines' meanings
            for o in q["options"]:
                assert not LATIN_WORDS.search(o["label"] or ""), (q["type"], o)


def test_every_internet_post_explains_itself_in_chinese(client, zh):
    assert all(i["summary"].get("zh") and all(n["tr"].get("zh") for n in i["notes"]) for i in ITEMS)
    item = expect(client, "get", f"/api/internet/items/{ITEMS[0]['slug']}", 200, headers=zh)
    assert item["summary"] == ITEMS[0]["summary"]["zh"]
    assert all(not LATIN_WORDS.search(n["text"]) for n in item["notes"]), item["notes"]


@pytest.mark.parametrize("locale", ["ru", "tg"])
def test_a_mistake_reads_in_the_language_the_learner_uses_now(client, locale):
    uid, h = register(client, unique_name("mixlang"))
    with SessionLocal() as db:
        word = db.query(models.VocabularyWord).filter_by(simplified="我").first()
        tr = (db.query(models.ContentTranslation)
              .filter_by(content_type="vocab_word", content_key=str(word.id), field="meanings", locale=locale).first().text)
        # Recorded during an English round: the question is the English gloss.
        db.add(models.LearningMistake(user_id=uid, mistake_type="word", reference="我",
                                      question_text=word.meanings, correct_answer="我 wǒ"))
        db.commit()
    mistakes = expect(client, "get", "/api/mistakes", 200, headers={**h, "X-Locale": locale})
    assert mistakes[0]["question_text"] == tr
    assert mistakes[0]["correct_answer"] == "我 wǒ"  # Chinese stays Chinese
    home = expect(client, "get", "/api/dashboard", 200, headers={**h, "X-Locale": locale})
    assert home["recent_mistakes"][0]["question_text"] == tr
