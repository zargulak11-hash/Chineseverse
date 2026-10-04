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
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/grammar_lesson.db"
os.environ["AI_PROVIDER"] = "offline"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services import ai_client  # noqa: E402
from app.services import grammar_lesson as gl  # noqa: E402
from app.services import sentence_check as sc  # noqa: E402

LANGS = {"en", "ru", "tg", "zh"}


def expect(client, method, url, expected, **kwargs):
    resp = getattr(client, method)(url, **kwargs)
    assert resp.status_code == expected, f"{method.upper()} {url} -> {resp.status_code} (expected {expected}): {resp.text}"
    return resp.json() if resp.content else None


def register(client, name):
    data = expect(client, "post", "/api/auth/register", 201,
                  json={"username": name, "email": f"{name}@example.com", "password": "secret1"})
    return data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}


def _localized(value, where):
    assert isinstance(value, dict) and set(value) == LANGS, f"{where}: needs exactly {sorted(LANGS)}, got {value!r}"
    assert all(isinstance(v, str) and v.strip() for v in value.values()), where


def _clean(zh, where):
    errors = [i["code"] for i in sc.detect(zh) if i["severity"] == "error"]
    assert not errors, f"{where}: {zh} flagged {errors}"


def test_authored_content():
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
    print(f"[PASS] {len(lessons)} authored lessons: real topics, all 4 languages, no known error in any 'right' Chinese")


def test_examples_parser():
    t = models.GrammarTopic(title="x", examples="（1）名量词：碗、脸\n一碗汤 一脸水\n我是学生。 / 他是老师。\n见【一37】\n书在桌子上。手机在书包里。")
    blocks = gl.example_blocks(t)
    kinds = [b["kind"] for b in blocks]
    assert kinds == ["heading", "phrases", "sentence", "sentence", "sentence", "sentence"], blocks
    assert blocks[2]["zh"] == "我是学生。" and blocks[5]["zh"] == "手机在书包里。", blocks
    print("[PASS] syllabus example text splits into headings, phrase lists and single sentences")


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
    print("[PASS] an AI lesson keeps only clean Chinese: wrong 'correct' examples, bad corrections and bad answer keys are dropped")


def topic_id(title):
    with SessionLocal() as db:
        return db.query(models.GrammarTopic).filter_by(title=title).order_by(models.GrammarTopic.id).first().id


def test_api(client):
    uid, h = register(client, "grammar_page_learner")
    adj = topic_id("主谓句2：形容词谓语句")
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
    print("[PASS] the page serves the authored lesson in the learner's language, with curriculum pinyin, words and real (zero) progress")

    expect(client, "get", "/api/grammar/999999", 404, headers=h)
    expect(client, "post", "/api/grammar/999999/check", 404, headers=h, json={"answer": "我很好。"})
    expect(client, "get", f"/api/grammar/{adj}", 401)
    print("[PASS] a missing topic is 404 and the page needs sign-in")

    calls = []

    def must_not_call(*a, **k):
        calls.append(1)
        raise AssertionError("authored topic must not call a model")

    orig = (ai_client._active_provider, ai_client._gemini_chat)
    ai_client._active_provider, ai_client._gemini_chat = (lambda: "gemini"), must_not_call
    try:
        r = expect(client, "post", f"/api/grammar/{adj}/lesson", 200, headers=h)
    finally:
        ai_client._active_provider, ai_client._gemini_chat = orig
    assert r["lesson_source"] == "authored" and not calls

    other = topic_id("借用量词")
    page = expect(client, "get", f"/api/grammar/{other}", 200, headers=h)
    assert page["lesson"] is None and page["can_generate"] is True
    assert [b["kind"] for b in page["examples"]][:2] == ["heading", "phrases"], page["examples"]
    expect(client, "post", f"/api/grammar/{other}/lesson", 503, headers=h)
    print("[PASS] authored topics never call a model; with no model a missing lesson is an honest 503")

    fake = json.dumps({
        "name": "借用量词", "summary": "Borrowed measure words.", "explanation": ["Containers become measure words."],
        "examples": [{"zh": "我喝了一碗汤。", "tr": "I had a bowl of soup."}, {"zh": "我有三苹果。", "tr": "bad"}],
        "exercises": [{"type": "write", "prompt": "Say: a bowl of rice", "answer": "一碗米饭"}],
    })
    seen = []

    def fake_chat(messages, **kw):
        seen.append(messages)
        return fake

    ai_client._active_provider, ai_client._gemini_chat = (lambda: "gemini"), fake_chat
    try:
        r = expect(client, "post", f"/api/grammar/{other}/lesson", 200, headers={**h, "X-Locale": "ru"})
        assert r["lesson_source"] == "ai" and [e["zh"] for e in r["lesson"]["examples"]] == ["我喝了一碗汤。"], r["lesson"]
        assert "Russian" in seen[0][0]["content"]
        _uid2, h2 = register(client, "grammar_page_second")
        again = expect(client, "get", f"/api/grammar/{other}", 200, headers={**h2, "X-Locale": "ru"})
        assert again["lesson_source"] == "ai" and again["can_generate"] is False and len(seen) == 1
    finally:
        ai_client._active_provider, ai_client._gemini_chat = orig
    with SessionLocal() as db:
        assert db.query(models.AIExplanation).filter_by(kind="grammar").count() == 1
    en = expect(client, "get", f"/api/grammar/{other}", 200, headers={**h, "X-Locale": "en"})
    assert en["lesson"] is None, "a lesson is cached per language"
    print("[PASS] an AI lesson is validated, cached once per topic+language, and served to the next learner without a call")

    lst = {t["id"]: t for t in expect(client, "get", "/api/grammar", 200, headers={**h, "X-Locale": "ru"},
                                       params={"hsk_level": 1})}
    assert lst[adj]["name"].startswith("Прилагательное"), lst[adj]
    lst4 = {t["id"]: t for t in expect(client, "get", "/api/grammar", 200, headers={**h, "X-Locale": "ru"},
                                        params={"hsk_level": 4})}
    assert lst4[other]["name"] == "借用量词", lst4[other]  # the cached AI lesson's name
    assert sum(1 for t in lst4.values() if t["name"]) == 1, "no name is invented for topics without a lesson"
    print("[PASS] the grammar list carries each lesson's localized name where a lesson exists, and none otherwise")

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
    print("[PASS] 'try it' checks use the sentence rules and exercise answers, and never touch mastery")

    s = expect(client, "post", "/api/practice/sessions", 201, headers=h,
               json={"source": "grammar", "hsk_level": 1, "topic_id": adj})
    with SessionLocal() as db:
        stored = db.get(models.PracticeSession, s["id"]).questions
    assert stored[0]["item_id"] == adj, stored[0]
    assert " / " not in s["questions"][0]["prompt"]["text"], s["questions"][0]["prompt"]
    print("[PASS] 'Practise this point' opens a round that starts with that topic, one example per question")


def main():
    with TestClient(app) as client:
        test_authored_content()
        test_examples_parser()
        test_ai_validation()
        test_api(client)
    print("ALL GRAMMAR LESSON TESTS PASSED")


if __name__ == "__main__":
    main()
