"""The in-app assistant is a real conversational assistant: with a live model
configured every question (greetings, Chinese grammar, general topics) goes to
the model with the learner's real database context, in the app's selected
language (X-Locale). The offline helper is used only when no model is
configured or the call fails, and then says so honestly instead of claiming
the question was off-topic."""

import os
import re
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/assistant.db"
# Never reach a real provider from a test, whatever backend/.env says.
os.environ["AI_PROVIDER"] = "offline"

import httpx  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services import ai_client  # noqa: E402

CYRILLIC = re.compile(r"[А-Яа-яЁё]")
TAJIK = re.compile(r"[ҲҳӢӣҶҷӮӯҒғҚқ]")
LATIN_WORD = re.compile(r"\b(?!HSK\b|DNA\b|XP\b|AI\b|asklearner\b|ChineseVerse\b|Pet\b|Teacher\b|le\b|ma\b|de\b)[A-Za-z]{3,}\b")
# The old catch-all refusal, in every language it existed in.
REFUSALS = ("only help with", "помогаю только", "танҳо дар ChineseVerse", "我只能帮助")


def chat(client, headers, text, locale=None, history=None):
    h = dict(headers)
    if locale:
        h["X-Locale"] = locale
    messages = (history or []) + [{"role": "user", "content": text}]
    resp = client.post("/api/assistant/chat", headers=h, json={"messages": messages})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for phrase in REFUSALS:
        assert phrase not in body["reply"], body["reply"]
    return body


def assert_language(reply, locale):
    if locale == "en":
        assert not CYRILLIC.search(reply), reply
    elif locale in ("ru", "tg"):
        assert CYRILLIC.search(reply), reply
        assert not LATIN_WORD.search(reply), reply
        if locale == "tg":
            assert TAJIK.search(reply), reply
    elif locale == "zh":
        assert not CYRILLIC.search(reply) and not LATIN_WORD.search(reply), reply


with TestClient(app) as client:
    data = client.post("/api/auth/register",
                       json={"username": "asklearner", "email": "asklearner@example.com", "password": "secret1"}).json()
    h = {"Authorization": f"Bearer {data['access_token']}"}
    user_id = data["user"]["id"]

    # --- offline fallback (no model configured) --------------------------
    questions = {
        "greet": "hello",
        "level": "how is my hsk progress?",
        "streak": "what is my streak?",
        "weak": "what should I improve?",
        "le": "了",
        "xp": "how do I get coins?",
        "companion": "who is my companion?",
        "duel": "tell me about duels",
        "general": "what's the weather?",
    }
    for locale in ("en", "ru", "tg", "zh"):
        table = ai_client.ASSISTANT_OFFLINE[locale]
        for key, text in questions.items():
            body = chat(client, h, text, locale)
            reply = body["reply"]
            assert body["source"] == "offline", body
            assert reply.startswith(table["unavailable"]), (locale, key, reply)
            assert_language(reply, locale)
            if key in ("le", "xp", "duel"):
                assert reply.endswith(table[key]), (locale, key, reply)
    print("[PASS] offline fallback is honest ('AI unavailable'), localized, and never the old refusal")

    for locale, text in [("tg", "Салом"), ("ru", "Привет"), ("en", "Hi!"), ("zh", "你好")]:
        reply = chat(client, h, text, locale)["reply"]
        assert "asklearner" in reply, (locale, reply)  # the greeting, not the generic line
        assert_language(reply, locale)
    # "this" contains "hi" -- must not be read as a greeting.
    assert "asklearner" not in chat(client, h, "what is this word about grammar in China?", "en")["reply"]
    print("[PASS] offline greetings are recognized in every language")

    for locale, text, key in [
        ("ru", "какой у меня прогресс?", "level"),
        ("ru", "расскажи про дуэли", "duel"),
        ("tg", "пешрафти ман чӣ хел?", "level"),
        ("tg", "дар бораи дуэл нақл кун", "duel"),
        ("zh", "我的进度怎么样", "level"),
        ("zh", "怎么获得金币", "xp"),
    ]:
        reply = chat(client, h, text, locale)["reply"]
        table = ai_client.ASSISTANT_OFFLINE[locale]
        if key in ("xp", "duel"):
            assert reply.endswith(table[key]), (locale, text, reply)
        else:
            assert "HSK" in reply and table["general"][:10] not in reply, (locale, text, reply)
        assert_language(reply, locale)
    print("[PASS] offline topic keywords work in the learner's own language")

    ru_weak = chat(client, h, "what should I improve?", "ru")["reply"]
    assert "Speaking" not in ru_weak and "Listening" not in ru_weak, ru_weak
    assert chat(client, h, "what's the weather?", "de")["reply"].startswith(ai_client.ASSISTANT_OFFLINE["en"]["unavailable"])
    print("[PASS] weak skills localized; unsupported X-Locale falls back to English")

    # --- a real mistake in the database, to verify context is real --------
    db = SessionLocal()
    db.add(models.LearningMistake(
        user_id=user_id, mistake_type="grammar", reference="了 vs 过",
        answer_given="过", correct_answer="了", last_seen_at=datetime.utcnow(),
    ))
    db.commit()
    xp_before = db.get(models.User, user_id).total_xp
    progress_before = db.query(models.Progress).filter_by(user_id=user_id).count()
    db.close()

    # --- live model path ---------------------------------------------------
    captured = []
    orig_provider, orig_chat = ai_client._active_provider, ai_client._openai_chat

    def fake_model(messages, model=None, max_tokens=200, temperature=0.8):
        captured.append({"messages": messages, "max_tokens": max_tokens})
        return f"generated answer #{len(captured)}"

    ai_client._active_provider = lambda: "openai"
    ai_client._openai_chat = fake_model
    try:
        cases = [
            ("tg", "Салом"),
            ("ru", "Привет"),
            ("en", "Hello"),
            ("zh", "你好"),
            ("tg", "Ман мехоҳам забони хитоиро омӯзам. Аз куҷо сар кунам?"),
            ("ru", "Что такое 了?"),
            ("en", "Explain HSK 3."),
            ("en", "How can I improve my Chinese vocabulary?"),
            ("zh", "我想学习中文。"),
            ("ru", "Какие места стоит посетить в Китае?"),
            ("ru", "Что такое искусственный интеллект?"),
            ("en", "Tell me an interesting fact."),
            ("ru", "Я сегодня плохо прошёл практику."),
            ("en", "What can you do?"),
            ("en", "What is my current HSK level and weakest skill?"),
        ]
        for locale, text in cases:
            body = chat(client, h, text, locale)
            assert body["source"] == "ai", body
            assert body["reply"] == f"generated answer #{len(captured)}", body
            sent = captured[-1]["messages"]
            # Every question reaches the model verbatim -- no topic gate in front.
            assert sent[-1] == {"role": "user", "content": text}, sent[-1]
            system = sent[0]
            assert system["role"] == "system"
            name = ai_client.ASSISTANT_LANGUAGE_NAMES[locale]
            assert f"always reply in {name}" in system["content"], system["content"]
        print("[PASS] greetings, Chinese questions and general questions all go to the model, in the selected language")

        prompt = captured[-1]["messages"][0]["content"]
        assert "ONLY help" not in prompt and "decline" not in prompt, prompt
        assert "Do not refuse them" in prompt
        assert "never invent" in prompt and "read-only" in prompt
        assert "current HSK level: 1" in prompt, prompt
        assert "items due in Review now: 1" in prompt, prompt  # the one open mistake
        assert "grammar 了 vs 过 (answered 过, correct 了)" in prompt, prompt
        assert "lessons completed: 0" in prompt, prompt
        assert "main companion: none chosen yet" in prompt, prompt
        assert "secret" not in prompt.lower() and "api_key" not in prompt.lower()
        assert captured[-1]["max_tokens"] >= 500  # room for a real answer
        print("[PASS] system prompt is open, carries only real database context, and no secrets")

        # Conversation history is forwarded so follow-ups make sense.
        history = [{"role": "user", "content": "Что такое 了?"}, {"role": "assistant", "content": "…"}]
        chat(client, h, "А приведи ещё пример", "ru", history=history)
        assert captured[-1]["messages"][1:] == history + [{"role": "user", "content": "А приведи ещё пример"}]
        print("[PASS] conversation history reaches the model")

        # Provider failure (429 exhausted credits, network, empty reply) -> localized fallback, no 500.
        def quota(messages, **kw):
            req = httpx.Request("POST", "https://example.invalid/chat/completions")
            raise httpx.HTTPStatusError("429", request=req, response=httpx.Response(429, request=req))
        def unreachable(messages, **kw):
            raise httpx.ConnectError("unreachable")
        def empty(messages, **kw):
            raise ValueError("AI provider returned an empty reply")
        for failure in (quota, unreachable, empty):
            ai_client._openai_chat = failure
            for locale in ("en", "ru", "tg", "zh"):
                body = chat(client, h, "Какие места стоит посетить в Китае?", locale)
                assert body["source"] == "offline", body
                assert body["reply"].startswith(ai_client.ASSISTANT_OFFLINE[locale]["unavailable"]), body
                assert_language(body["reply"], locale)
        print("[PASS] AI failure degrades to a localized 'temporarily unavailable' fallback")
    finally:
        ai_client._active_provider, ai_client._openai_chat = orig_provider, orig_chat

    # The assistant is read-only: dozens of chats changed no XP or lesson progress.
    db = SessionLocal()
    assert db.get(models.User, user_id).total_xp == xp_before
    assert db.query(models.Progress).filter_by(user_id=user_id).count() == progress_before
    db.close()
    print("[PASS] chatting never changes XP or progress")

    assert client.post("/api/assistant/chat", json={"messages": [{"role": "user", "content": "hi"}]}).status_code == 401
    print("[PASS] assistant requires authentication")

# --- transport: Gemini through the OpenAI-compatible endpoint ---------------
sent = {}


def fake_post(url, headers=None, json=None, timeout=None):
    sent.update(url=url, headers=headers, json=json)
    req = httpx.Request("POST", url)
    return httpx.Response(200, request=req, json={"choices": [{"message": {"content": sent.get("reply", "  你好！  ")}}]})


orig_post = httpx.post
saved = (settings.ai_provider, settings.ai_api_key, settings.gemini_api_key, settings.ai_base_url, settings.ai_model)
httpx.post = fake_post
try:
    settings.ai_provider, settings.ai_api_key, settings.gemini_api_key = "auto", None, "test-gemini-key"
    settings.ai_base_url, settings.ai_model = None, None
    assert ai_client._active_provider() == "openai"
    assert ai_client._openai_chat([{"role": "user", "content": "hi"}], max_tokens=700) == "你好！"
    assert sent["url"] == ai_client.GEMINI_BASE_URL + "/chat/completions", sent["url"]
    assert sent["json"]["model"] == ai_client.GEMINI_MODEL
    assert sent["json"]["max_tokens"] == 700
    assert sent["json"]["reasoning_effort"] == "none"
    assert sent["headers"]["Authorization"] == "Bearer test-gemini-key"

    settings.ai_provider, settings.ai_api_key, settings.gemini_api_key = "openai", "test-openai-key", None
    ai_client._openai_chat([{"role": "user", "content": "hi"}])
    assert sent["url"] == ai_client.OPENAI_BASE_URL + "/chat/completions"
    assert sent["json"]["model"] == ai_client.OPENAI_MODEL and "reasoning_effort" not in sent["json"]

    sent["reply"] = "   "
    try:
        ai_client._openai_chat([{"role": "user", "content": "hi"}])
        raise AssertionError("empty reply must raise")
    except ValueError:
        pass

    settings.ai_provider, settings.ai_api_key = "openai", None
    assert ai_client._active_provider() == "offline"  # no key -> offline, not a failing call
    settings.ai_provider = "gemini"
    assert ai_client._active_provider() == "offline"
    print("[PASS] Gemini/OpenAI transport: endpoint, model, auth and empty-reply handling")
finally:
    httpx.post = orig_post
    settings.ai_provider, settings.ai_api_key, settings.gemini_api_key, settings.ai_base_url, settings.ai_model = saved

print("ALL ASSISTANT TESTS PASSED")
