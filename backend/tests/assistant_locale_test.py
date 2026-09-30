"""The in-app assistant answers in the app's selected language (X-Locale),
both through the AI provider and through the offline fallback."""

import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/assistant.db"

import httpx  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services import ai_client  # noqa: E402

CYRILLIC = re.compile(r"[А-Яа-яЁё]")
TAJIK = re.compile(r"[ҲҳӢӣҶҷӮӯҒғҚқ]")
LATIN_WORD = re.compile(r"\b(?!HSK\b|DNA\b|XP\b|ChineseVerse\b|Pet\b|Teacher\b|le\b|ma\b|de\b)[A-Za-z]{3,}\b")


def chat(client, headers, text, locale=None):
    h = dict(headers)
    if locale:
        h["X-Locale"] = locale
    resp = client.post("/api/assistant/chat", headers=h, json={"messages": [{"role": "user", "content": text}]})
    assert resp.status_code == 200, resp.text
    return resp.json()["reply"]


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

    # --- offline fallback: every topic, every locale, in the selected language
    questions = {
        "level": "how is my hsk progress?",
        "streak": "what is my streak?",
        "weak": "what should I improve?",
        "le": "了",
        "xp": "how do I get coins?",
        "companion": "who is my companion?",
        "duel": "tell me about duels",
        "offtopic": "what's the weather?",
    }
    for locale in ("en", "ru", "tg", "zh"):
        table = ai_client.ASSISTANT_OFFLINE[locale]
        for key, text in questions.items():
            reply = chat(client, h, text, locale)
            assert_language(reply, locale)
            if key in ("le", "xp", "duel", "offtopic"):
                assert reply == table[key], (locale, key, reply)
    print("[PASS] offline replies follow X-Locale for en/ru/tg/zh on every topic")

    # The learner may type in their own language; the topic is still recognized.
    for locale, text, key in [
        ("ru", "какой у меня прогресс?", "level"),
        ("ru", "расскажи про дуэли", "duel"),
        ("tg", "пешрафти ман чӣ хел?", "level"),
        ("tg", "дар бораи дуэл нақл кун", "duel"),
        ("zh", "我的进度怎么样", "level"),
        ("zh", "怎么获得金币", "xp"),
    ]:
        reply = chat(client, h, text, locale)
        if key in ("xp", "duel"):
            assert reply == ai_client.ASSISTANT_OFFLINE[locale][key], (locale, text, reply)
        else:
            assert reply != ai_client.ASSISTANT_OFFLINE[locale]["offtopic"], (locale, text, reply)
        assert_language(reply, locale)
    print("[PASS] offline topic keywords work in the learner's own language")

    # Weak-skill names are the localized skill names, not the English column.
    ru_weak = chat(client, h, "what should I improve?", "ru")
    assert "Speaking" not in ru_weak and "Listening" not in ru_weak, ru_weak
    print("[PASS] weak skills are named in the selected language")

    # Missing or unsupported header -> the original English replies.
    assert chat(client, h, "what's the weather?") == ai_client.ASSISTANT_OFFLINE["en"]["offtopic"]
    assert chat(client, h, "what's the weather?", "de") == ai_client.ASSISTANT_OFFLINE["en"]["offtopic"]
    print("[PASS] missing/unsupported X-Locale falls back to English")

    # --- AI provider path: the system prompt names the selected language
    captured = []
    orig_provider, orig_chat = ai_client._active_provider, ai_client._openai_chat
    ai_client._active_provider = lambda: "openai"
    ai_client._openai_chat = lambda messages, model: captured.append(messages) or "stub reply"
    try:
        for locale, name in ai_client.ASSISTANT_LANGUAGE_NAMES.items():
            assert chat(client, h, "hello", locale) == "stub reply"
            system = captured[-1][0]
            assert system["role"] == "system"
            assert f"always reply in {name}" in system["content"], system["content"]
        print("[PASS] AI system prompt instructs the model to answer in the selected language")

        # AI failure -> offline fallback, still in the selected language.
        def boom(messages, model):
            raise httpx.ConnectError("unreachable")
        ai_client._openai_chat = boom
        assert chat(client, h, "what's the weather?", "tg") == ai_client.ASSISTANT_OFFLINE["tg"]["offtopic"]
        assert chat(client, h, "what's the weather?", "zh") == ai_client.ASSISTANT_OFFLINE["zh"]["offtopic"]
        print("[PASS] AI failure falls back offline in the selected language")
    finally:
        ai_client._active_provider, ai_client._openai_chat = orig_provider, orig_chat

print("ALL ASSISTANT LOCALE TESTS PASSED")
