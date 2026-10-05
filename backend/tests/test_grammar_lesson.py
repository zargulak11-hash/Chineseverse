"""Grammar points are full learning pages, built from real data.

Covers:
  * every authored lesson (seed_content/grammar/*.json) names a real topic,
    has every human-language field in en/ru/tg/zh, and none of its "right"
    Chinese (examples, negatives, questions, dialogue, corrected mistakes,
    exercise answers) trips a known-error rule; every "choose" exercise has
    exactly its marked answer as the clean option;
  * GET /api/grammar/{id}: localized authored lesson, pinyin computed from
    the curriculum, syllabus examples split into sentences/phrases/headings,
    real progress (0 for a new learner), related points, 404 for a missing id;
  * POST /lesson: authored topics never call a model; with no model the
    answer is an honest 503; a model's lesson is validated (wrong Chinese
    dropped), cached once and served to the next learner without a call;
  * POST /check: rules verdicts, exercise targets, and that checking never
    changes mastery;
  * a grammar practice round opened from a page starts with that topic.
"""

import json

import pytest

from app import models
from app.database import SessionLocal
from app.services import ai_client
from app.services import grammar_lesson as gl
from app.services import sentence_check as sc
from helpers import expect, register, unique_name

LANGS = {"en", "ru", "tg", "zh"}


def _localized(value, where):
    assert isinstance(value, dict) and set(value) == LANGS, f"{where}: needs exactly {sorted(LANGS)}, got {value!r}"
    assert all(isinstance(v, str) and v.strip() for v in value.values()), where


def _clean(zh, where):
    errors = [i["code"] for i in sc.detect(zh) if i["severity"] == "error"]
    assert not errors, f"{where}: {zh} flagged {errors}"


def test_authored_content(client):
    with SessionLocal() as db:
        titles = {t.title for t in db.query(models.GrammarTopic).all()}
    lessons = gl.authored()
    assert len(lessons) >= 10, len(lessons)
    for topic, data in lessons.items():
        w = f"[{topic}]"
        assert topic in titles, f"{w} is not a grammar topic title in the curriculum"
        for key in ("name", "summary"):
            _localized(data[key], f"{w}.{key}")
        for key in ("when_to_use", "when_not", "explanation", "deeper"):
            for i, v in enumerate(data.get(key) or []):
                _localized(v, f"{w}.{key}[{i}]")
        for i, s in enumerate(data["structure"]):
            _localized(s["formula"], f"{w}.structure[{i}]")
            _clean(s["zh"], f"{w}.structure[{i}]")
        for key in ("examples", "negative", "questions", "dialogue"):
            for i, e in enumerate(data.get(key) or []):
                _clean(e["zh"], f"{w}.{key}[{i}]")
                assert set(e["tr"]) == {"en", "ru", "tg"}, f"{w}.{key}[{i}].tr"
                if e.get("note"):
                    _localized(e["note"], f"{w}.{key}[{i}].note")
        assert len(data["examples"]) >= 4, w
        assert data["mistakes"], w
        for i, m in enumerate(data["mistakes"]):
            _clean(m["right"], f"{w}.mistakes[{i}].right")
            assert sc.normalize(m["wrong"]) != sc.normalize(m["right"]), f"{w}.mistakes[{i}]"
            _localized(m["why"], f"{w}.mistakes[{i}].why")
        for i, s in enumerate(data.get("similar") or []):
            _localized(s["difference"], f"{w}.similar[{i}]")
            assert s.get("topic") is None or s["topic"] in titles, f"{w}.similar[{i}].topic {s.get('topic')}"
        if data.get("register"):
            _localized(data["register"], f"{w}.register")
        assert data["exercises"], w
        for i, e in enumerate(data["exercises"]):
            _localized(e["prompt"], f"{w}.exercises[{i}].prompt")
            if e["type"] == "choose":
                _clean(e["options"][e["answer"]], f"{w}.exercises[{i}] answer")
                _localized(e["why"], f"{w}.exercises[{i}].why")
            else:
                _clean(e["answer"], f"{w}.exercises[{i}].answer")
                assert sc.check(e["answer"], e["answer"])["verdict"] == "correct"


def test_examples_parser():
    t = models.GrammarTopic(title="x", examples="（1）名量词：碗、脸\n一碗汤 一脸水\n我是学生。 / 他是老师。\n见【一37】\n书在桌子上。手机在书包里。")
    blocks = gl.example_blocks(t)
    kinds = [b["kind"] for b in blocks]
    assert kinds == ["heading", "phrases", "sentence", "sentence", "sentence", "sentence"], blocks
    assert blocks[2]["zh"] == "我是学生。" and blocks[5]["zh"] == "手机在书包里。", blocks


def test_ai_validation():
    raw = {
        "name": "x", "summary": "s", "explanation": ["p"], "structure": [{"formula": "S + 很 + Adj", "zh": "我很高兴。"}],
        "examples": [{"zh": "我很高兴。", "tr": "I'm happy"}, {"zh": "我是很高兴。", "tr": "bad"}, {"zh": "hello", "tr": "no"}],
        "mistakes": [{"wrong": "我是很累。", "right": "我很累。", "why": "w"}, {"wrong": "我很累。", "right": "我是很累。", "why": "w"},
                     {"wrong": "a", "right": "a", "why": "w"}],
        "exercises": [{"type": "choose", "prompt": "p", "options": ["我是很高兴。", "我很高兴。"], "answer": 0, "why": "w"},
                      {"type": "choose", "prompt": "p", "options": ["我是很高兴。", "我很高兴。"], "answer": 1, "why": "w"},
                      {"type": "write", "prompt": "p", "answer": "我很累。"}],
    }
    out = gl.validate_ai_lesson(raw)
    assert [e["zh"] for e in out["examples"]] == ["我很高兴。"], out["examples"]
    assert [m["right"] for m in out["mistakes"]] == ["我很累。"], out["mistakes"]
    assert [e["answer"] for e in out["exercises"]] == [1, "我很累。"], out["exercises"]
    assert gl.validate_ai_lesson({"name": "x"}) is None and gl.validate_ai_lesson("nope") is None


def topic_id(title):
    with SessionLocal() as db:
        return db.query(models.GrammarTopic).filter_by(title=title).order_by(models.GrammarTopic.id).first().id


ADJ = "主谓句2：形容词谓语句"  # has an authored lesson
BORROWED = "借用量词"  # has none


@pytest.fixture
def learner(client):
    return register(client, unique_name("grammar_page"))


@pytest.fixture
def model(monkeypatch):
    """model(reply) pretends Gemini is configured and answers with `reply`
    (a callable); returns the list of prompts it received."""
    def install(reply):
        seen = []

        def chat(messages, **kw):
            seen.append(messages)
            return reply(messages)

        monkeypatch.setattr(ai_client, "_active_provider", lambda: "gemini")
        monkeypatch.setattr(ai_client, "_gemini_chat", chat)
        return seen
    return install


def test_the_page_serves_the_authored_lesson_localized_with_real_progress(client, learner):
    _, h = learner
    adj = topic_id(ADJ)
    page = expect(client, "get", f"/api/grammar/{adj}", 200, headers={**h, "X-Locale": "ru"})
    assert page["lesson_source"] == "authored" and page["can_generate"] is False
    assert page["lesson"]["name"].startswith("Прилагательное"), page["lesson"]["name"]
    assert page["lesson"]["examples"][0]["zh"] == "我很高兴。"
    assert page["lesson"]["examples"][0]["pinyin"], page["lesson"]["examples"][0]
    assert page["lesson"]["examples"][0]["tr"] == "Я рад(а).", page["lesson"]["examples"][0]
    assert any(w["text"] == "高兴" for w in page["lesson"]["examples"][0]["words"])
    assert page["progress"] == {"status": "new", "mastery": 0.0, "times_practiced": 0, "due": False, "next_review_at": None}
    assert any(s.get("topic_id") for s in page["lesson"]["similar"]), page["lesson"]["similar"]
    assert page["examples"] and page["examples"][0]["kind"] == "sentence" and page["examples"][0]["pinyin"]
    assert page["vocabulary"] and page["pet_teacher_cases"] >= 1
    zh = expect(client, "get", f"/api/grammar/{adj}", 200, headers={**h, "X-Locale": "zh"})
    assert zh["lesson"]["examples"][0]["tr"] is None and zh["lesson"]["summary"].startswith("汉语")


def test_a_missing_topic_is_404_and_the_page_needs_sign_in(client, learner):
    _, h = learner
    expect(client, "get", "/api/grammar/999999", 404, headers=h)
    expect(client, "post", "/api/grammar/999999/check", 404, headers=h, json={"answer": "我很好。"})
    expect(client, "get", f"/api/grammar/{topic_id(ADJ)}", 401)


def test_authored_topics_never_call_a_model(client, learner, model):
    _, h = learner

    def must_not_call(messages):
        raise AssertionError("authored topic must not call a model")

    seen = model(must_not_call)
    r = expect(client, "post", f"/api/grammar/{topic_id(ADJ)}/lesson", 200, headers=h)
    assert r["lesson_source"] == "authored" and not seen


def test_without_a_model_a_missing_lesson_is_an_honest_503(client, learner):
    _, h = learner
    other = topic_id(BORROWED)
    page = expect(client, "get", f"/api/grammar/{other}", 200, headers=h)
    assert page["lesson"] is None and page["can_generate"] is True
    assert [b["kind"] for b in page["examples"]][:2] == ["heading", "phrases"], page["examples"]
    expect(client, "post", f"/api/grammar/{other}/lesson", 503, headers=h)


def test_an_ai_lesson_is_validated_cached_per_language_and_named_in_the_list(client, learner, model):
    _, h = learner
    adj, other = topic_id(ADJ), topic_id(BORROWED)
    fake = json.dumps({
        "name": "借用量词", "summary": "Borrowed measure words.", "explanation": ["Containers become measure words."],
        "examples": [{"zh": "我喝了一碗汤。", "tr": "I had a bowl of soup."}, {"zh": "我有三苹果。", "tr": "bad"}],
        "exercises": [{"type": "write", "prompt": "Say: a bowl of rice", "answer": "一碗米饭"}],
    })
    seen = model(lambda messages: fake)
    r = expect(client, "post", f"/api/grammar/{other}/lesson", 200, headers={**h, "X-Locale": "ru"})
    assert r["lesson_source"] == "ai" and [e["zh"] for e in r["lesson"]["examples"]] == ["我喝了一碗汤。"], r["lesson"]
    assert "Russian" in seen[0][0]["content"]
    _, h2 = register(client, unique_name("grammar_second"))
    again = expect(client, "get", f"/api/grammar/{other}", 200, headers={**h2, "X-Locale": "ru"})
    assert again["lesson_source"] == "ai" and again["can_generate"] is False and len(seen) == 1
    with SessionLocal() as db:
        assert db.query(models.AIExplanation).filter_by(kind="grammar").count() == 1
    en = expect(client, "get", f"/api/grammar/{other}", 200, headers={**h, "X-Locale": "en"})
    assert en["lesson"] is None, "a lesson is cached per language"

    # the list carries each lesson's localized name where a lesson exists, and none otherwise
    lst = {t["id"]: t for t in expect(client, "get", "/api/grammar", 200, headers={**h, "X-Locale": "ru"},
                                       params={"hsk_level": 1})}
    assert lst[adj]["name"].startswith("Прилагательное"), lst[adj]
    lst4 = {t["id"]: t for t in expect(client, "get", "/api/grammar", 200, headers={**h, "X-Locale": "ru"},
                                        params={"hsk_level": 4})}
    assert lst4[other]["name"] == "借用量词", lst4[other]  # the cached AI lesson's name
    assert sum(1 for t in lst4.values() if t["name"]) == 1, "no name is invented for topics without a lesson"


def test_try_it_checks_use_the_rules_and_never_touch_mastery(client, learner):
    uid, h = learner
    adj = topic_id(ADJ)
    r = expect(client, "post", f"/api/grammar/{adj}/check", 200, headers=h, json={"answer": "我是很高兴。"})
    assert r["verdict"] == "incorrect" and r["issues"] == ["shi_adj"], r
    r = expect(client, "post", f"/api/grammar/{adj}/check", 200, headers=h, json={"answer": "天气很好。"})
    assert r["verdict"] == "unchecked" and r["issues"] == [], r
    lesson = expect(client, "get", f"/api/grammar/{adj}", 200, headers=h)["lesson"]
    wi = next(i for i, e in enumerate(lesson["exercises"]) if e["type"] == "write")
    ci = next(i for i, e in enumerate(lesson["exercises"]) if e["type"] == "choose")
    r = expect(client, "post", f"/api/grammar/{adj}/check", 200, headers=h, json={"answer": "我很累", "exercise": wi})
    assert r["verdict"] == "correct", r
    r = expect(client, "post", f"/api/grammar/{adj}/check", 200, headers=h, json={"answer": "我是很累。", "exercise": wi})
    assert r["verdict"] == "incorrect" and r["expected"] == "我很累。", r
    expect(client, "post", f"/api/grammar/{adj}/check", 404, headers=h, json={"answer": "我很累", "exercise": ci})
    expect(client, "post", f"/api/grammar/{adj}/check", 422, headers=h, json={"answer": "hello"})
    with SessionLocal() as db:
        assert db.query(models.UserGrammar).filter_by(user_id=uid).count() == 0


def test_practise_this_point_opens_a_round_starting_with_that_topic(client, learner):
    _, h = learner
    adj = topic_id(ADJ)
    s = expect(client, "post", "/api/practice/sessions", 201, headers=h,
               json={"source": "grammar", "hsk_level": 1, "topic_id": adj})
    with SessionLocal() as db:
        stored = db.get(models.PracticeSession, s["id"]).questions
    assert stored[0]["item_id"] == adj, stored[0]
    assert " / " not in s["questions"][0]["prompt"]["text"], s["questions"][0]["prompt"]
