"""AI failures degrade to the offline behaviour -- never to an error.

Gemini is configured (a test key) but the HTTP transport fails in the ways
a real provider does: unreachable, a 500, an overload that outlasts the
retry, or a 200 whose body is not what was asked for. Every model-backed
entry point must then return exactly what it returns on a server with no
key at all -- the same grade, the same reply, the same "nothing invented".
No request leaves the test process."""

import httpx
import pytest

from app import models
from app.config import settings
from app.database import SessionLocal
from app.routers import assistant as assistant_router
from app.services import ai_client, voice_eval
from helpers import register, unique_name

FAILURES = {
    "unreachable": lambda req: httpx.ConnectError("unreachable", request=req),
    "server-error": lambda req: httpx.Response(500, request=req, json={"error": {"code": 500}}),
    "overloaded": lambda req: httpx.Response(503, request=req, json={"error": {"code": 503}}),
    "blocked-200": lambda req: httpx.Response(200, request=req, json={"promptFeedback": {"blockReason": "SAFETY"}}),
    # Only meaningful for the graders that ask for JSON: for a free-text
    # reply, "not json {" is a valid answer.
    "malformed-json-200": lambda req: httpx.Response(200, request=req, json={"candidates": [{"content": {"parts": [{"text": "not json {"}]}}]}),
}
JSON_GRADERS = {"explain_reading", "grammar_lesson", "evaluate_case_solution", "judge_sentence",
                "pet_teacher_explanation", "voice_grading"}


@pytest.fixture(scope="module")
def context(client):
    """A real learner's assistant context (what the endpoint would pass)."""
    uid, _ = register(client, unique_name("ai_ctx"))
    with SessionLocal() as db:
        return assistant_router._learner_context(db, db.get(models.User, uid), "ru")


def calls(context):
    """name -> zero-argument call of one AI entry point."""
    chat = [{"role": "user", "content": "你好，你叫什么名字？"}]
    return {
        "chat_reply": lambda: ai_client.chat_reply(chat, animal_slug="fox", user_name="learner", energy=3, level_hint="beginner"),
        "translate_sentence": lambda: ai_client.translate_sentence("我昨天去了北京。", "ru"),
        "explain_reading": lambda: ai_client.explain_reading("我叫王小雨。", "ru", 1, [{"text": "叫", "meaning": "to be called"}], []),
        "grammar_lesson": lambda: ai_client.grammar_lesson("借用量词", "一碗汤", ["我喝了一碗汤。"], "ru", 4),
        "evaluate_case_solution": lambda: ai_client.evaluate_case_solution("案情", "顾客是对的，老板错了", ["顾客", "老板"], "提示"),
        "judge_sentence": lambda: ai_client.judge_sentence("我很开心。", "我很高兴。", "Correct: 我是很高兴。", "ru", wrong="我是很高兴。"),
        "pet_teacher_explanation": lambda: ai_client.evaluate_pet_teacher_explanation(
            "是 is not used before adjectives", "adjective is the predicate, no 是", ["是", "adjective"],
            wrong_sentence="我是很高兴。", correct_sentence="我很高兴。", correction="我很高兴。", correction_ok=True, locale="ru"),
        "assistant_reply": lambda: ai_client.assistant_reply(chat, context, "ru"),
        "assistant_stream": lambda: list(ai_client.assistant_stream(chat, context, "ru")),
        "voice_grading": lambda: voice_eval.grade_turn(None, "我要一碗牛肉面", expected_keywords=["牛肉面"]),
    }


@pytest.fixture
def offline_results(context, monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "offline")
    ai_client._translation_cache.clear()
    return {name: call() for name, call in calls(context).items()}


@pytest.mark.parametrize("name, failure", [
    (name, failure) for name in calls({}) for failure in FAILURES
    if failure != "malformed-json-200" or name in JSON_GRADERS
])
def test_a_failing_provider_gives_exactly_the_offline_result(context, offline_results, monkeypatch, name, failure):
    sent = []

    def fake_post(url, headers=None, json=None, timeout=None):
        sent.append(url)
        outcome = FAILURES[failure](httpx.Request("POST", url))
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def fake_stream(method, url, **kw):
        sent.append(url)
        raise httpx.ConnectError("unreachable", request=httpx.Request(method, url))

    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "stream", fake_stream)
    monkeypatch.setattr(ai_client.time, "sleep", lambda s: None)
    ai_client._cooling_until.clear()
    ai_client._translation_cache.clear()

    result = calls(context)[name]()  # must not raise

    expected = offline_results[name]
    if name == "assistant_stream":
        # The live path announces itself before failing over; the text is the offline one.
        text = lambda ev: "".join(e.get("text", "") for e in ev if e["type"] == "delta")
        assert text(result) == text(expected) and result[-1] == {"type": "done"}, result
    else:
        assert result == expected
    assert sent, "the provider was really tried"
    ai_client._cooling_until.clear()
