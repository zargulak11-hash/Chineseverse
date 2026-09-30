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
    orig_provider, orig_chat = ai_client._active_provider, ai_client._gemini_chat

    def fake_model(messages, max_tokens=200, temperature=0.8, json_mode=False):
        captured.append({"messages": messages, "max_tokens": max_tokens})
        return f"generated answer #{len(captured)}"

    ai_client._active_provider = lambda: "gemini"
    ai_client._gemini_chat = fake_model
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
            ("ru", "Привет, как дела?"),
            ("tg", "Ман мехоҳам забони чиниро омӯзам"),
            ("en", "What is HSK?"),
            ("en", "What places can I visit in China?"),
            ("en", "What is AI?"),
            ("zh", "我的HSK水平和最薄弱的技能是什么？"),
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

        # Provider failure (429 quota, network, blocked/empty reply) -> localized fallback, no 500.
        def quota(messages, **kw):
            req = httpx.Request("POST", "https://example.invalid/models/x:generateContent")
            raise httpx.HTTPStatusError("429", request=req, response=httpx.Response(429, request=req))
        def unreachable(messages, **kw):
            raise httpx.ConnectError("unreachable")
        def empty(messages, **kw):
            raise ValueError("AI provider returned an empty reply")
        for failure in (quota, unreachable, empty):
            ai_client._gemini_chat = failure
            for locale in ("en", "ru", "tg", "zh"):
                body = chat(client, h, "Какие места стоит посетить в Китае?", locale)
                assert body["source"] == "offline", body
                assert body["reply"].startswith(ai_client.ASSISTANT_OFFLINE[locale]["unavailable"]), body
                assert_language(body["reply"], locale)
        print("[PASS] AI failure degrades to a localized 'temporarily unavailable' fallback")
    finally:
        ai_client._active_provider, ai_client._gemini_chat = orig_provider, orig_chat

    # The assistant is read-only: dozens of chats changed no XP or lesson progress.
    db = SessionLocal()
    assert db.get(models.User, user_id).total_xp == xp_before
    assert db.query(models.Progress).filter_by(user_id=user_id).count() == progress_before
    db.close()
    print("[PASS] chatting never changes XP or progress")

    assert client.post("/api/assistant/chat", json={"messages": [{"role": "user", "content": "hi"}]}).status_code == 401
    print("[PASS] assistant requires authentication")

# --- transport: the real Gemini request the app sends (httpx mocked) --------
sent = {}


def fake_post(url, headers=None, json=None, timeout=None):
    sent.update(url=url, headers=headers, json=json)
    req = httpx.Request("POST", url)
    if "response" in sent:
        return httpx.Response(200, request=req, json=sent["response"])
    return httpx.Response(200, request=req, json={
        "candidates": [{"content": {"role": "model", "parts": [{"text": "  Салом! "}, {"text": "Биёед оғоз кунем."}]},
                        "finishReason": "STOP"}]})


orig_post = httpx.post
saved = (settings.ai_provider, settings.gemini_api_key, settings.gemini_model, settings.gemini_base_url)
httpx.post = fake_post
try:
    settings.ai_provider, settings.gemini_api_key = "gemini", "test-gemini-key"
    settings.gemini_model = "gemini-2.5-flash"
    settings.gemini_base_url = "https://generativelanguage.googleapis.com/v1beta"
    assert ai_client._active_provider() == "gemini"

    # End to end through the real endpoint: the HTTP request that leaves the
    # app is a Gemini generateContent call carrying the user's message.
    with TestClient(app) as client:
        tok = client.post("/api/auth/login", json={"username": "asklearner", "password": "secret1"})
        assert tok.status_code == 200, tok.text
        hh = {"Authorization": f"Bearer {tok.json()['access_token']}", "X-Locale": "tg"}
        history = [{"role": "user", "content": "Салом"}, {"role": "assistant", "content": "Салом!"}]
        r = client.post("/api/assistant/chat", headers=hh, json={"messages": history + [
            {"role": "user", "content": "Ман мехоҳам забони чиниро омӯзам"}]})
        assert r.status_code == 200 and r.json() == {"reply": "Салом! Биёед оғоз кунем.", "source": "ai"}, r.text
    assert sent["url"] == "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent", sent["url"]
    assert "key=" not in sent["url"]  # key travels in a header, never the URL
    assert sent["headers"] == {"x-goog-api-key": "test-gemini-key"}
    body = sent["json"]
    assert body["contents"] == [
        {"role": "user", "parts": [{"text": "Салом"}]},
        {"role": "model", "parts": [{"text": "Салом!"}]},
        {"role": "user", "parts": [{"text": "Ман мехоҳам забони чиниро омӯзам"}]},
    ], body["contents"]
    assert "always reply in Tajik" in body["systemInstruction"]["parts"][0]["text"]
    assert body["generationConfig"]["maxOutputTokens"] == 700
    assert body["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 0}
    assert "responseMimeType" not in body["generationConfig"]
    print("[PASS] assistant endpoint sends a real Gemini generateContent request (URL, header auth, roles, locale)")

    # JSON graders ask Gemini for JSON output.
    sent["response"] = {"candidates": [{"content": {"parts": [{"text": '{"solved": true, "feedback": "对"}'}]}}]}
    assert ai_client.evaluate_case_solution("案情", "是他", ["他"])["solved"] is True
    assert sent["json"]["generationConfig"]["responseMimeType"] == "application/json"

    # Blocked prompt (no candidates) / empty text -> ValueError -> callers fall back.
    for bad in ({"promptFeedback": {"blockReason": "SAFETY"}},
                {"candidates": [{"finishReason": "SAFETY"}]},
                {"candidates": [{"content": {"parts": [{"text": "   "}]}}]}):
        sent["response"] = bad
        try:
            ai_client._gemini_chat([{"role": "user", "content": "hi"}])
            raise AssertionError(f"must raise for {bad}")
        except ValueError:
            pass
    assert ai_client.evaluate_case_solution("案情", "是他", ["他"]) == {"solved": True, "feedback": ""}
    print("[PASS] blocked/empty Gemini responses raise and callers degrade offline")

    # No Gemini key -> offline without any request; a stale AI_PROVIDER=openai
    # never routes anywhere but Gemini/offline.
    settings.ai_provider = "openai"
    assert ai_client._active_provider() == "gemini"
    settings.gemini_api_key = None
    assert ai_client._active_provider() == "offline"
    settings.ai_provider, settings.gemini_api_key = "offline", "test-gemini-key"
    assert ai_client._active_provider() == "offline"
    print("[PASS] provider resolution: Gemini with a key, offline otherwise")
finally:
    httpx.post = orig_post
    settings.ai_provider, settings.gemini_api_key, settings.gemini_model, settings.gemini_base_url = saved

print("ALL ASSISTANT TESTS PASSED")
