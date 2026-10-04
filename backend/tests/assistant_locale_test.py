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
from app.routers import assistant as _assistant_router  # noqa: E402

# This test sends hundreds of turns from one account; the hourly cap is
# covered by assistant_stream_test.
_assistant_router.CHATS_PER_HOUR = 100_000
from app.services.dna import bump_skill  # noqa: E402
from app.services.gamification import ensure_user_skills  # noqa: E402

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
            ("ru", "Как подготовиться к HSK 3?"),
            ("ru", "Что посмотреть в Китае?"),
            ("ru", "Какой у меня прогресс?"),
            ("ru", "Какой у меня самый слабый навык?"),
            ("ru", "Что ты умеешь?"),
            ("tg", "Ман мехоҳам забони хитоиро омӯзам."),
            ("ru", "Как лучше подготовиться к HSK?"),
            ("ru", "Что ты можешь делать?"),
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

        # TG: the rule pins Tajik Cyrillic and rules out the look-alike
        # languages, at the very top of the prompt and again at the end.
        chat(client, h, "What is artificial intelligence?", "tg")
        tg_system = captured[-1]["messages"][0]["content"]
        assert tg_system.startswith("REPLY LANGUAGE: Tajik. Write in Tajik (тоҷикӣ)"), tg_system[:200]
        assert tg_system.count("Tajik Cyrillic alphabet") == 2, tg_system
        for word in ("ғ, ӣ, қ, ӯ, ҳ, ҷ", "Russian, Uzbek, Persian/Farsi", "Latin or"):
            assert word in tg_system, word
        chat(client, h, "Hello", "en")
        assert "Tajik" not in captured[-1]["messages"][0]["content"]
        print("[PASS] TG prompt pins Tajik Cyrillic (not Russian/Uzbek/Persian), top and bottom")

        # Mixed-script letters inside Tajik words are repaired -- the two
        # glitches seen live from gemini-flash-lite -- while whole Latin words,
        # pinyin and Chinese are left untouched.
        clean = ai_client._tg_clean_mixed_script
        assert clean("Бо کмоли майл") == "Бо кмоли майл"  # Arabic kaf -> Cyrillic к
        assert clean("супуrтани имтиҳон") == "супуртани имтиҳон"
        assert clean("ChineseVerse, HSK 1, 北京 (Běijīng), streak") == "ChineseVerse, HSK 1, 北京 (Běijīng), streak"
        assert clean("**了 (le)** — ҳиссача") == "**了 (le)** — ҳиссача"

        def glitchy(messages, **kw):
            captured.append({"messages": messages, "max_tokens": kw.get("max_tokens")})
            return "Барои супуrтани HSK (Hànyǔ)"
        ai_client._gemini_chat = glitchy
        assert chat(client, h, "Салом", "tg")["reply"] == "Барои супуртани HSK (Hànyǔ)"
        assert chat(client, h, "Привет", "ru")["reply"] == "Барои супуrтани HSK (Hànyǔ)"  # other locales untouched
        ai_client._gemini_chat = fake_model
        print("[PASS] stray Latin/Arabic letters inside Tajik words are repaired for TG only")

        prompt = captured[-1]["messages"][0]["content"]
        assert "ONLY help" not in prompt and "decline" not in prompt, prompt
        # Focused on Chinese learning, but greetings are welcome and nothing
        # is refused rudely; no pretend web search or live data.
        assert "Do not refuse rudely" in prompt and "small talk are welcome" in prompt
        assert "no internet access, no web search" in prompt
        assert "never invent" in prompt and "read-only" in prompt
        assert "current HSK level on the lesson path: 1" in prompt, prompt
        assert "final exam" not in prompt, prompt  # HSK 1 lessons aren't done yet
        # The real lesson path position, in the learner's language (this prompt was a ru request).
        assert 'current lesson on the lesson path: "Приветствия" (HSK 1)' in prompt, prompt
        assert "items due in Review now: 1" in prompt, prompt  # the one open mistake
        assert "grammar 了 vs 过 (answered 过, correct 了)" in prompt, prompt
        assert "lessons completed: 0" in prompt, prompt
        assert "main companion: none chosen yet" in prompt, prompt
        assert "Learning Compass overall: 0.0%" in prompt and "vocabulary words mastered: 0" in prompt, prompt
        # No practice yet: every skill is 0, so there is no weakest one to name.
        assert "weakest Learning Compass skills: not enough practice yet to tell" in prompt, prompt
        assert "skill mastery" not in prompt, prompt
        assert "secret" not in prompt.lower() and "api_key" not in prompt.lower()
        assert captured[-1]["max_tokens"] >= 500  # room for a real answer
        print("[PASS] system prompt is open, carries only real database context, and no secrets")

        # Real Learning DNA data reaches the model once it exists (written
        # through the same bump_skill the practice grader uses).
        db = SessionLocal()
        u = db.get(models.User, user_id)
        ensure_user_skills(db, u)
        bump_skill(u, "speaking", 55)
        bump_skill(u, "grammar", 12)
        db.commit()
        db.close()
        chat(client, h, "Какой у меня самый слабый навык?", "ru")
        prompt = captured[-1]["messages"][0]["content"]
        weak_line = next(l for l in prompt.splitlines() if l.startswith("- weakest Learning Compass skills:"))
        assert "not enough practice" not in weak_line and "Speaking" not in weak_line, weak_line
        mastery_line = next(l for l in prompt.splitlines() if l.startswith("- Learning Compass skill mastery:"))
        assert "12%" in mastery_line and "55%" in mastery_line, mastery_line
        assert mastery_line.index("12%") < mastery_line.index("55%")  # weakest first
        print("[PASS] real Learning DNA skill mastery is passed, weakest first, in the selected language")

        # At the exam gate the next step is the level's final exam, not a lesson.
        from app.services.lesson_path import path_state
        db = SessionLocal()
        u = db.get(models.User, user_id)
        for e in path_state(db, u).entries:
            if e.level == 1 and e.practicable:
                db.add(models.Progress(user_id=user_id, lesson_id=e.lesson.id, status="completed", score=90))
        db.commit()
        # (a deliberate write, like the DNA one above; chatting must add nothing on top)
        progress_before = db.query(models.Progress).filter_by(user_id=user_id).count()
        db.close()
        chat(client, h, "Что мне делать дальше?", "ru")
        prompt = captured[-1]["messages"][0]["content"]
        assert "the next step is the HSK 1 final exam" in prompt, prompt
        assert "current lesson on the lesson path" not in prompt, prompt
        print("[PASS] at the exam gate the assistant is told the HSK 1 final exam is next")

        # Snapshot after the deliberate DNA write: chatting itself must not move anything.
        db = SessionLocal()
        u = db.get(models.User, user_id)
        skills_before = {s.skill_id: s.mastery for s in u.user_skills}
        streak_before = u.streak.current_streak if u.streak else None
        db.close()

        # Conversation history is forwarded so follow-ups make sense.
        history = [{"role": "user", "content": "Что такое 了?"}, {"role": "assistant", "content": "…"}]
        chat(client, h, "А приведи ещё пример", "ru", history=history)
        assert captured[-1]["messages"][1:] == history + [{"role": "user", "content": "А приведи ещё пример"}]
        print("[PASS] conversation history reaches the model")

        # Provider failure -> localized fallback in the same response shape, no 500.
        def http_error(status):
            def fail(messages, **kw):
                req = httpx.Request("POST", "https://example.invalid/models/x:generateContent")
                raise httpx.HTTPStatusError(str(status), request=req, response=httpx.Response(status, request=req))
            return fail
        def unreachable(messages, **kw):
            raise httpx.ConnectError("unreachable")
        def timeout(messages, **kw):
            raise httpx.ReadTimeout("timed out")
        def empty(messages, **kw):
            raise ValueError("Gemini returned no text")
        failures = (http_error(429), http_error(500), http_error(502), http_error(503),
                    http_error(401), http_error(403), unreachable, timeout, empty)
        for failure in failures:
            ai_client._gemini_chat = failure
            for locale in ("en", "ru", "tg", "zh"):
                body = chat(client, h, "Какие места стоит посетить в Китае?", locale)
                assert set(body) == {"reply", "source"} and body["source"] == "offline", body
                assert body["reply"].startswith(ai_client.ASSISTANT_OFFLINE[locale]["unavailable"]), body
                assert_language(body["reply"], locale)
        print("[PASS] 429/500/502/503/401/403/network/timeout/empty all degrade to the localized fallback")
    finally:
        ai_client._active_provider, ai_client._gemini_chat = orig_provider, orig_chat

    # Missing key: offline straight away, without attempting a request.
    saved_key = settings.gemini_api_key
    settings.ai_provider, settings.gemini_api_key = "gemini", None
    try:
        body = chat(client, h, "Что ты умеешь?", "ru")
        assert body["source"] == "offline" and body["reply"].startswith(ai_client.ASSISTANT_OFFLINE["ru"]["unavailable"])
    finally:
        settings.ai_provider, settings.gemini_api_key = "offline", saved_key
    print("[PASS] missing Gemini key -> localized fallback")

    # The assistant is read-only: dozens of chats changed no XP, lesson
    # progress, Learning DNA mastery or streak.
    db = SessionLocal()
    u = db.get(models.User, user_id)
    assert u.total_xp == xp_before
    assert db.query(models.Progress).filter_by(user_id=user_id).count() == progress_before
    assert {s.skill_id: s.mastery for s in u.user_skills} == skills_before
    assert (u.streak.current_streak if u.streak else None) == streak_before
    db.close()
    print("[PASS] chatting never changes XP, progress, Learning DNA or streak")

    assert client.post("/api/assistant/chat", json={"messages": [{"role": "user", "content": "hi"}]}).status_code == 401
    print("[PASS] assistant requires authentication")

# --- transport: the real Gemini request the app sends (httpx mocked) --------
sent = {}
calls = []          # every outgoing request URL, in order
script = []         # queued per-call outcomes: int status, "timeout", or a JSON body
OK = {"candidates": [{"content": {"role": "model", "parts": [{"text": "  Салом! "}, {"text": "Биёед оғоз кунем."}]},
                      "finishReason": "STOP"}]}


def fake_post(url, headers=None, json=None, timeout=None):
    sent.update(url=url, headers=headers, json=json)
    calls.append(url)
    req = httpx.Request("POST", url)
    outcome = script.pop(0) if script else OK
    if outcome == "timeout":
        raise httpx.ReadTimeout("timed out", request=req)
    if isinstance(outcome, int):
        return httpx.Response(outcome, request=req, json={"error": {"code": outcome}})
    return httpx.Response(200, request=req, json=outcome)


def model_of(url):
    return url.rsplit("/models/", 1)[1].split(":")[0]


BASE = "https://generativelanguage.googleapis.com/v1beta"
orig_post, orig_sleep = httpx.post, ai_client.time.sleep
saved = (settings.ai_provider, settings.gemini_api_key, settings.gemini_model,
         settings.gemini_fallback_models, settings.gemini_base_url)
httpx.post = fake_post
ai_client.time.sleep = lambda s: None
try:
    settings.ai_provider, settings.gemini_api_key = "gemini", "test-gemini-key"
    settings.gemini_model, settings.gemini_base_url = "gemini-3.8-flash", BASE
    settings.gemini_fallback_models = ["gemini-3.5-flash", "gemini-flash-lite-latest"]
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
    assert sent["url"] == f"{BASE}/models/gemini-3.8-flash:generateContent", sent["url"]
    assert "key=" not in sent["url"]  # key travels in a header, never the URL
    assert sent["headers"] == {"x-goog-api-key": "test-gemini-key"}
    body = sent["json"]
    assert body["contents"] == [
        {"role": "user", "parts": [{"text": "Салом"}]},
        {"role": "model", "parts": [{"text": "Салом!"}]},
        {"role": "user", "parts": [{"text": "Ман мехоҳам забони чиниро омӯзам"}]},
    ], body["contents"]
    system_text = body["systemInstruction"]["parts"][0]["text"]
    assert "always reply in Tajik" in system_text and "current HSK level on the lesson path" in system_text
    # Visible answer budget + headroom for the model's hidden thinking, and
    # no model-specific thinking flags (gemini-3.x rejects some of them).
    # 1500: room for a full grammar explanation (meaning, structure, examples, mistakes).
    assert body["generationConfig"]["maxOutputTokens"] == 1500 + ai_client.THINKING_HEADROOM
    assert "thinkingConfig" not in body["generationConfig"]
    assert "responseMimeType" not in body["generationConfig"]
    print("[PASS] assistant endpoint sends a real Gemini generateContent request (URL, header auth, roles, context, locale)")

    msg = [{"role": "user", "content": "hi"}]

    def run(*outcomes, keep_cooldowns=False):
        calls.clear()
        if not keep_cooldowns:
            ai_client._cooling_until.clear()
        script[:] = list(outcomes)
        try:
            return ai_client._gemini_chat(msg), [model_of(u) for u in calls]
        finally:
            script.clear()

    # Retired model (404) / daily quota (429) -> next model in the chain.
    assert run(404) == ("Салом! Биёед оғоз кунем.", ["gemini-3.8-flash", "gemini-3.5-flash"])
    assert run(429, 429) == ("Салом! Биёед оғоз кунем.",
                             ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-flash-lite-latest"])
    # Overload: one quick retry on the same model first.
    assert run(503)[1] == ["gemini-3.8-flash", "gemini-3.8-flash"]
    assert run(503, 503)[1] == ["gemini-3.8-flash", "gemini-3.8-flash", "gemini-3.5-flash"]
    assert run(502, 502)[1] == ["gemini-3.8-flash", "gemini-3.8-flash", "gemini-3.5-flash"]
    # Timeout -> next model.
    assert run("timeout")[1] == ["gemini-3.8-flash", "gemini-3.5-flash"]
    # Bad key / bad request won't be fixed by another model: fail fast.
    for status in (400, 401, 403):
        try:
            run(status)
            raise AssertionError(f"{status} must raise")
        except httpx.HTTPStatusError:
            assert [model_of(u) for u in calls] == ["gemini-3.8-flash"], calls
    # Every model exhausted -> the last error is raised (callers fall back).
    try:
        run(429, 429, 429)
        raise AssertionError("must raise when every model fails")
    except httpx.HTTPStatusError as exc:
        assert exc.response.status_code == 429
    assert len(calls) == 3
    print("[PASS] model chain: 404/429/timeout -> next model, 502/503 retried once, 4xx auth errors fail fast")

    # A model out of quota is skipped on the following messages instead of
    # costing an extra failed round trip every time...
    assert run(429)[1] == ["gemini-3.8-flash", "gemini-3.5-flash"]
    assert run(keep_cooldowns=True)[1] == ["gemini-3.5-flash"]
    assert run(429, keep_cooldowns=True)[1] == ["gemini-3.5-flash", "gemini-flash-lite-latest"]
    assert run(keep_cooldowns=True)[1] == ["gemini-flash-lite-latest"]
    # ...an overload (503) is not remembered...
    ai_client._cooling_until.clear()
    run(503, 503)
    assert run(keep_cooldowns=True)[1] == ["gemini-3.8-flash"]
    # ...and with every model cooling down, all are still tried.
    for m in ("gemini-3.8-flash", "gemini-3.5-flash", "gemini-flash-lite-latest"):
        ai_client._cooling_until[m] = ai_client.time.monotonic() + 600
    assert run(keep_cooldowns=True)[1] == ["gemini-3.8-flash"]
    assert "gemini-3.8-flash" not in ai_client._cooling_until  # success clears it
    ai_client._cooling_until.clear()
    print("[PASS] quota-exhausted / retired models are skipped for a cooldown, overloads are not")

    # JSON graders ask Gemini for JSON output.
    script[:] = [{"candidates": [{"content": {"parts": [{"text": '{"solved": true, "feedback": "对"}'}]}}]}]
    assert ai_client.evaluate_case_solution("案情", "是他", ["他"])["solved"] is True
    assert sent["json"]["generationConfig"]["responseMimeType"] == "application/json"

    # Blocked prompt (no candidates) / empty text -> ValueError -> callers fall back.
    for bad in ({"promptFeedback": {"blockReason": "SAFETY"}},
                {"candidates": [{"finishReason": "SAFETY"}]},
                {"candidates": [{"content": {"parts": [{"text": "   "}]}}]},
                {"candidates": [{"content": {"parts": [{"text": "hidden", "thought": True}]}}]}):
        script[:] = [bad]
        try:
            ai_client._gemini_chat(msg)
            raise AssertionError(f"must raise for {bad}")
        except ValueError:
            pass
    script[:] = [{"candidates": []}]
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
    httpx.post, ai_client.time.sleep = orig_post, orig_sleep
    (settings.ai_provider, settings.gemini_api_key, settings.gemini_model,
     settings.gemini_fallback_models, settings.gemini_base_url) = saved

print("ALL ASSISTANT TESTS PASSED")
