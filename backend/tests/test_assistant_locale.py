"""The in-app assistant is a real conversational assistant: with a live model
configured every question (greetings, Chinese grammar, general topics) goes to
the model with the learner's real database context, in the app's selected
language (X-Locale). The offline helper is used only when no model is
configured or the call fails, and then says so honestly instead of claiming
the question was off-topic. No test reaches a real provider: the model call
or the HTTP transport is replaced."""

import re
from datetime import datetime
from types import SimpleNamespace

import httpx
import pytest

from app import models
from app.config import settings
from app.database import SessionLocal
from app.routers import assistant as assistant_router
from app.services import ai_client
from app.services.dna import bump_skill
from app.services.gamification import ensure_user_skills
from app.services.lesson_path import path_state
from helpers import bearer, expect, register, unique_name

CYRILLIC = re.compile(r"[А-Яа-яЁё]")
TAJIK = re.compile(r"[ҲҳӢӣҶҷӮӯҒғҚқ]")
LATIN_WORD = re.compile(r"\b(?!HSK\b|DNA\b|XP\b|AI\b|asklearner\b|ChineseVerse\b|Pet\b|Teacher\b|le\b|ma\b|de\b)[A-Za-z]{3,}\b")
# The old catch-all refusal, in every language it existed in.
REFUSALS = ("only help with", "помогаю только", "танҳо дар ChineseVerse", "我只能帮助")
LOCALES = ("en", "ru", "tg", "zh")


@pytest.fixture(scope="module", autouse=True)
def no_hourly_cap():
    # These tests send hundreds of turns; the cap has its own test in
    # test_assistant_stream.py.
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(assistant_router, "CHATS_PER_HOUR", 100_000)
        yield


def chat(client, headers, text, locale=None, history=None):
    h = dict(headers)
    if locale:
        h["X-Locale"] = locale
    messages = (history or []) + [{"role": "user", "content": text}]
    body = expect(client, "post", "/api/assistant/chat", 200, headers=h, json={"messages": messages})
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


@pytest.fixture(scope="module")
def asklearner(client):
    """The learner the offline answers greet by name."""
    return register(client, "asklearner")[1]


@pytest.fixture
def learner_with_a_mistake(client):
    """A new learner whose only record is one open grammar mistake."""
    uid, h = register(client, unique_name("ctx"))
    with SessionLocal() as db:
        db.add(models.LearningMistake(
            user_id=uid, mistake_type="grammar", reference="了 vs 过",
            answer_given="过", correct_answer="了", last_seen_at=datetime.utcnow(),
        ))
        db.commit()
    return uid, h


@pytest.fixture
def model(monkeypatch):
    """A configured model that answers "generated answer #n"; returns the
    list of {"messages", "max_tokens"} it was called with."""
    captured = []

    def fake_model(messages, max_tokens=200, temperature=0.8, json_mode=False):
        captured.append({"messages": messages, "max_tokens": max_tokens})
        return f"generated answer #{len(captured)}"

    monkeypatch.setattr(ai_client, "_active_provider", lambda: "gemini")
    monkeypatch.setattr(ai_client, "_gemini_chat", fake_model)
    return captured


def system_prompt(captured):
    return captured[-1]["messages"][0]["content"]


# --- offline fallback (no model configured) -----------------------------------

OFFLINE_QUESTIONS = {
    "greet": "hello", "level": "how is my hsk progress?", "streak": "what is my streak?",
    "weak": "what should I improve?", "le": "了", "xp": "how do I get coins?",
    "companion": "who is my companion?", "duel": "tell me about duels", "general": "what's the weather?",
}


@pytest.mark.parametrize("locale", LOCALES)
def test_offline_answers_are_honest_and_localized(client, asklearner, locale):
    table = ai_client.ASSISTANT_OFFLINE[locale]
    for key, text in OFFLINE_QUESTIONS.items():
        body = chat(client, asklearner, text, locale)
        reply = body["reply"]
        assert body["source"] == "offline", body
        assert reply.startswith(table["unavailable"]), (locale, key, reply)
        assert_language(reply, locale)
        if key in ("le", "xp", "duel"):
            assert reply.endswith(table[key]), (locale, key, reply)


@pytest.mark.parametrize("locale, text", [("tg", "Салом"), ("ru", "Привет"), ("en", "Hi!"), ("zh", "你好")])
def test_offline_greetings_are_recognized_in_every_language(client, asklearner, locale, text):
    reply = chat(client, asklearner, text, locale)["reply"]
    assert "asklearner" in reply, (locale, reply)  # the greeting, not the generic line
    assert_language(reply, locale)


def test_a_word_containing_hi_is_not_a_greeting(client, asklearner):
    assert "asklearner" not in chat(client, asklearner, "what is this word about grammar in China?", "en")["reply"]


@pytest.mark.parametrize("locale, text, key", [
    ("ru", "какой у меня прогресс?", "level"), ("ru", "расскажи про дуэли", "duel"),
    ("tg", "пешрафти ман чӣ хел?", "level"), ("tg", "дар бораи дуэл нақл кун", "duel"),
    ("zh", "我的进度怎么样", "level"), ("zh", "怎么获得金币", "xp"),
])
def test_offline_topic_keywords_work_in_the_learners_own_language(client, asklearner, locale, text, key):
    reply = chat(client, asklearner, text, locale)["reply"]
    table = ai_client.ASSISTANT_OFFLINE[locale]
    if key in ("xp", "duel"):
        assert reply.endswith(table[key]), (locale, text, reply)
    else:
        assert "HSK" in reply and table["general"][:10] not in reply, (locale, text, reply)
    assert_language(reply, locale)


def test_offline_weak_skills_are_localized_and_unknown_locales_fall_back_to_english(client, asklearner):
    ru_weak = chat(client, asklearner, "what should I improve?", "ru")["reply"]
    assert "Speaking" not in ru_weak and "Listening" not in ru_weak, ru_weak
    reply = chat(client, asklearner, "what's the weather?", "de")["reply"]
    assert reply.startswith(ai_client.ASSISTANT_OFFLINE["en"]["unavailable"])


# --- live model path ----------------------------------------------------------

MODEL_CASES = [
    ("tg", "Салом"), ("ru", "Привет"), ("en", "Hello"), ("zh", "你好"),
    ("tg", "Ман мехоҳам забони хитоиро омӯзам. Аз куҷо сар кунам?"), ("ru", "Что такое 了?"),
    ("en", "Explain HSK 3."), ("en", "How can I improve my Chinese vocabulary?"), ("zh", "我想学习中文。"),
    ("ru", "Какие места стоит посетить в Китае?"), ("ru", "Что такое искусственный интеллект?"),
    ("en", "Tell me an interesting fact."), ("ru", "Я сегодня плохо прошёл практику."), ("en", "What can you do?"),
    ("ru", "Привет, как дела?"), ("tg", "Ман мехоҳам забони чиниро омӯзам"), ("en", "What is HSK?"),
    ("en", "What places can I visit in China?"), ("en", "What is AI?"), ("zh", "我的HSK水平和最薄弱的技能是什么？"),
    ("en", "What is my current HSK level and weakest skill?"), ("ru", "Как подготовиться к HSK 3?"),
    ("ru", "Что посмотреть в Китае?"), ("ru", "Какой у меня прогресс?"), ("ru", "Какой у меня самый слабый навык?"),
    ("ru", "Что ты умеешь?"), ("tg", "Ман мехоҳам забони хитоиро омӯзам."),
    ("ru", "Как лучше подготовиться к HSK?"), ("ru", "Что ты можешь делать?"),
]


def test_every_question_goes_to_the_model_in_the_selected_language(client, asklearner, model):
    for locale, text in MODEL_CASES:
        body = chat(client, asklearner, text, locale)
        assert body["source"] == "ai", body
        assert body["reply"] == f"generated answer #{len(model)}", body
        sent = model[-1]["messages"]
        # Every question reaches the model verbatim -- no topic gate in front.
        assert sent[-1] == {"role": "user", "content": text}, sent[-1]
        assert sent[0]["role"] == "system"
        name = ai_client.ASSISTANT_LANGUAGE_NAMES[locale]
        assert f"always reply in {name}" in sent[0]["content"], sent[0]["content"]


def test_the_tajik_prompt_pins_tajik_cyrillic_at_the_top_and_the_end(client, asklearner, model):
    chat(client, asklearner, "What is artificial intelligence?", "tg")
    tg_system = system_prompt(model)
    assert tg_system.startswith("REPLY LANGUAGE: Tajik. Write in Tajik (тоҷикӣ)"), tg_system[:200]
    assert tg_system.count("Tajik Cyrillic alphabet") == 2, tg_system
    for word in ("ғ, ӣ, қ, ӯ, ҳ, ҷ", "Russian, Uzbek, Persian/Farsi", "Latin or"):
        assert word in tg_system, word
    chat(client, asklearner, "Hello", "en")
    assert "Tajik" not in system_prompt(model)


def test_stray_latin_or_arabic_letters_in_tajik_words_are_repaired_for_tg_only(client, asklearner, monkeypatch):
    # The two glitches seen live from gemini-flash-lite; whole Latin words,
    # pinyin and Chinese are left untouched.
    clean = ai_client._tg_clean_mixed_script
    assert clean("Бо کмоли майл") == "Бо кмоли майл"  # Arabic kaf -> Cyrillic к
    assert clean("супуrтани имтиҳон") == "супуртани имтиҳон"
    assert clean("ChineseVerse, HSK 1, 北京 (Běijīng), streak") == "ChineseVerse, HSK 1, 北京 (Běijīng), streak"
    assert clean("**了 (le)** — ҳиссача") == "**了 (le)** — ҳиссача"
    monkeypatch.setattr(ai_client, "_active_provider", lambda: "gemini")
    monkeypatch.setattr(ai_client, "_gemini_chat", lambda messages, **kw: "Барои супуrтани HSK (Hànyǔ)")
    assert chat(client, asklearner, "Салом", "tg")["reply"] == "Барои супуртани HSK (Hànyǔ)"
    assert chat(client, asklearner, "Привет", "ru")["reply"] == "Барои супуrтани HSK (Hànyǔ)"  # other locales untouched


def test_the_system_prompt_is_open_and_carries_only_real_context_and_no_secrets(client, learner_with_a_mistake, model):
    _, h = learner_with_a_mistake
    chat(client, h, "Привет", "ru")
    prompt = system_prompt(model)
    assert "ONLY help" not in prompt and "decline" not in prompt, prompt
    # Focused on Chinese learning, but greetings are welcome and nothing
    # is refused rudely; no pretend web search or live data.
    assert "Do not refuse rudely" in prompt and "small talk are welcome" in prompt
    assert "no internet access, no web search" in prompt
    assert "never invent" in prompt and "read-only" in prompt
    assert "current HSK level on the lesson path: 1" in prompt, prompt
    assert "final exam" not in prompt, prompt  # HSK 1 lessons aren't done yet
    # The real lesson path position, in the learner's language (a ru request).
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
    assert model[-1]["max_tokens"] >= 500  # room for a real answer


def test_real_learning_compass_mastery_reaches_the_model_weakest_first(client, learner_with_a_mistake, model):
    uid, h = learner_with_a_mistake
    # Written through the same bump_skill the practice grader uses.
    with SessionLocal() as db:
        u = db.get(models.User, uid)
        ensure_user_skills(db, u)
        bump_skill(u, "speaking", 55)
        bump_skill(u, "grammar", 12)
        db.commit()
    chat(client, h, "Какой у меня самый слабый навык?", "ru")
    lines = system_prompt(model).splitlines()
    weak_line = next(l for l in lines if l.startswith("- weakest Learning Compass skills:"))
    assert "not enough practice" not in weak_line and "Speaking" not in weak_line, weak_line
    mastery_line = next(l for l in lines if l.startswith("- Learning Compass skill mastery:"))
    assert "12%" in mastery_line and "55%" in mastery_line, mastery_line
    assert mastery_line.index("12%") < mastery_line.index("55%")  # weakest first


def test_at_the_exam_gate_the_assistant_is_told_the_final_exam_is_next(client, learner_with_a_mistake, model):
    uid, h = learner_with_a_mistake
    with SessionLocal() as db:
        u = db.get(models.User, uid)
        for e in path_state(db, u).entries:
            if e.level == 1 and e.practicable:
                db.add(models.Progress(user_id=uid, lesson_id=e.lesson.id, status="completed", score=90))
        db.commit()
    chat(client, h, "Что мне делать дальше?", "ru")
    prompt = system_prompt(model)
    assert "the next step is the HSK 1 final exam" in prompt, prompt
    assert "current lesson on the lesson path" not in prompt, prompt


def test_conversation_history_reaches_the_model(client, asklearner, model):
    history = [{"role": "user", "content": "Что такое 了?"}, {"role": "assistant", "content": "…"}]
    chat(client, asklearner, "А приведи ещё пример", "ru", history=history)
    assert model[-1]["messages"][1:] == history + [{"role": "user", "content": "А приведи ещё пример"}]


def _http_error(status):
    def fail(messages, **kw):
        req = httpx.Request("POST", "https://example.invalid/models/x:generateContent")
        raise httpx.HTTPStatusError(str(status), request=req, response=httpx.Response(status, request=req))
    return fail


def _raise(exc):
    def fail(messages, **kw):
        raise exc
    return fail


@pytest.mark.parametrize("failure", [
    _http_error(429), _http_error(500), _http_error(502), _http_error(503), _http_error(401), _http_error(403),
    _raise(httpx.ConnectError("unreachable")), _raise(httpx.ReadTimeout("timed out")),
    _raise(ValueError("Gemini returned no text")),
], ids=["429", "500", "502", "503", "401", "403", "unreachable", "timeout", "empty"])
def test_a_provider_failure_degrades_to_the_localized_fallback(client, asklearner, monkeypatch, failure):
    monkeypatch.setattr(ai_client, "_active_provider", lambda: "gemini")
    monkeypatch.setattr(ai_client, "_gemini_chat", failure)
    for locale in LOCALES:
        body = chat(client, asklearner, "Какие места стоит посетить в Китае?", locale)
        assert set(body) == {"reply", "source"} and body["source"] == "offline", body
        assert body["reply"].startswith(ai_client.ASSISTANT_OFFLINE[locale]["unavailable"]), body
        assert_language(body["reply"], locale)


def test_a_missing_gemini_key_goes_offline_without_a_request(client, asklearner, monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", None)
    body = chat(client, asklearner, "Что ты умеешь?", "ru")
    assert body["source"] == "offline" and body["reply"].startswith(ai_client.ASSISTANT_OFFLINE["ru"]["unavailable"])


def test_chatting_never_changes_xp_progress_learning_compass_or_streak(client, learner_with_a_mistake, model):
    uid, h = learner_with_a_mistake

    def snapshot():
        with SessionLocal() as db:
            u = db.get(models.User, uid)
            ensure_user_skills(db, u)
            db.commit()
            return (u.total_xp, db.query(models.Progress).filter_by(user_id=uid).count(),
                    {s.skill_id: s.mastery for s in u.user_skills}, u.streak.current_streak if u.streak else None)

    before = snapshot()
    for locale, text in MODEL_CASES[:10]:
        chat(client, h, text, locale)
    assert snapshot() == before


def test_the_assistant_requires_sign_in(client):
    assert client.post("/api/assistant/chat", json={"messages": [{"role": "user", "content": "hi"}]}).status_code == 401


# --- transport: the real Gemini request the app sends (httpx mocked) ----------

BASE = "https://generativelanguage.googleapis.com/v1beta"
OK = {"candidates": [{"content": {"role": "model", "parts": [{"text": "  Салом! "}, {"text": "Биёед оғоз кунем."}]},
                      "finishReason": "STOP"}]}
MSG = [{"role": "user", "content": "hi"}]


def model_of(url):
    return url.rsplit("/models/", 1)[1].split(":")[0]


@pytest.fixture
def gemini(monkeypatch):
    """Gemini configured with a test key; httpx.post replaced by a scripted
    fake (each call takes the next outcome: an int status, "timeout", or a
    JSON body; OK when the script is empty). No sleeping between retries."""
    net = SimpleNamespace(sent={}, calls=[], script=[])

    def fake_post(url, headers=None, json=None, timeout=None):
        net.sent.update(url=url, headers=headers, json=json)
        net.calls.append(url)
        req = httpx.Request("POST", url)
        outcome = net.script.pop(0) if net.script else OK
        if outcome == "timeout":
            raise httpx.ReadTimeout("timed out", request=req)
        if isinstance(outcome, int):
            return httpx.Response(outcome, request=req, json={"error": {"code": outcome}})
        return httpx.Response(200, request=req, json=outcome)

    def run(*outcomes, keep_cooldowns=False):
        net.calls.clear()
        if not keep_cooldowns:
            ai_client._cooling_until.clear()
        net.script[:] = list(outcomes)
        try:
            return ai_client._gemini_chat(MSG), [model_of(u) for u in net.calls]
        finally:
            net.script.clear()

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(ai_client.time, "sleep", lambda s: None)
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "test-gemini-key")
    monkeypatch.setattr(settings, "gemini_model", "gemini-3.8-flash")
    monkeypatch.setattr(settings, "gemini_base_url", BASE)
    monkeypatch.setattr(settings, "gemini_fallback_models", ["gemini-3.5-flash", "gemini-flash-lite-latest"])
    ai_client._cooling_until.clear()
    net.run = run
    yield net
    ai_client._cooling_until.clear()


def test_the_endpoint_sends_a_real_generate_content_request(client, gemini):
    assert ai_client._active_provider() == "gemini"
    _, h = register(client, unique_name("transport"))
    history = [{"role": "user", "content": "Салом"}, {"role": "assistant", "content": "Салом!"}]
    r = client.post("/api/assistant/chat", headers={**h, "X-Locale": "tg"}, json={"messages": history + [
        {"role": "user", "content": "Ман мехоҳам забони чиниро омӯзам"}]})
    assert r.status_code == 200 and r.json() == {"reply": "Салом! Биёед оғоз кунем.", "source": "ai"}, r.text
    sent = gemini.sent
    assert sent["url"] == f"{BASE}/models/gemini-3.8-flash:generateContent", sent["url"]
    assert "key=" not in sent["url"]  # the key travels in a header, never the URL
    assert sent["headers"] == {"x-goog-api-key": "test-gemini-key"}
    body = sent["json"]
    assert body["contents"] == [
        {"role": "user", "parts": [{"text": "Салом"}]},
        {"role": "model", "parts": [{"text": "Салом!"}]},
        {"role": "user", "parts": [{"text": "Ман мехоҳам забони чиниро омӯзам"}]},
    ], body["contents"]
    system_text = body["systemInstruction"]["parts"][0]["text"]
    assert "always reply in Tajik" in system_text and "current HSK level on the lesson path" in system_text
    # Visible answer budget (room for a full grammar explanation) + headroom
    # for hidden thinking, and no model-specific thinking flags (gemini-3.x
    # rejects some of them).
    assert body["generationConfig"]["maxOutputTokens"] == 1500 + ai_client.THINKING_HEADROOM
    assert "thinkingConfig" not in body["generationConfig"]
    assert "responseMimeType" not in body["generationConfig"]


def test_the_model_chain_falls_through_and_fails_fast_on_auth_errors(gemini):
    run = gemini.run
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
        with pytest.raises(httpx.HTTPStatusError):
            run(status)
        assert [model_of(u) for u in gemini.calls] == ["gemini-3.8-flash"], gemini.calls
    # Every model exhausted -> the last error is raised (callers fall back).
    with pytest.raises(httpx.HTTPStatusError) as exc:
        run(429, 429, 429)
    assert exc.value.response.status_code == 429 and len(gemini.calls) == 3


def test_quota_exhausted_models_cool_down_but_overloads_do_not(gemini):
    run = gemini.run
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


def test_json_graders_ask_for_json_and_blocked_or_empty_answers_fall_back(gemini):
    gemini.script[:] = [{"candidates": [{"content": {"parts": [{"text": '{"solved": true, "feedback": "对"}'}]}}]}]
    assert ai_client.evaluate_case_solution("案情", "是他", ["他"])["solved"] is True
    assert gemini.sent["json"]["generationConfig"]["responseMimeType"] == "application/json"
    # Blocked prompt (no candidates) / empty text -> ValueError -> callers fall back.
    for bad in ({"promptFeedback": {"blockReason": "SAFETY"}},
                {"candidates": [{"finishReason": "SAFETY"}]},
                {"candidates": [{"content": {"parts": [{"text": "   "}]}}]},
                {"candidates": [{"content": {"parts": [{"text": "hidden", "thought": True}]}}]}):
        gemini.script[:] = [bad]
        with pytest.raises(ValueError):
            ai_client._gemini_chat(MSG)
    gemini.script[:] = [{"candidates": []}]
    assert ai_client.evaluate_case_solution("案情", "是他", ["他"]) == {"solved": True, "feedback": ""}


def test_provider_resolution_is_gemini_with_a_key_and_offline_otherwise(monkeypatch):
    # A stale AI_PROVIDER=openai never routes anywhere but Gemini/offline.
    monkeypatch.setattr(settings, "ai_provider", "openai")
    monkeypatch.setattr(settings, "gemini_api_key", "test-gemini-key")
    assert ai_client._active_provider() == "gemini"
    settings.gemini_api_key = None
    assert ai_client._active_provider() == "offline"
    settings.ai_provider, settings.gemini_api_key = "offline", "test-gemini-key"
    assert ai_client._active_provider() == "offline"


# --- a sentence the learner asks about ----------------------------------------

@pytest.mark.parametrize("locale", LOCALES)
def test_offline_explains_shi_before_an_adjective_not_ma(client, asklearner, locale):
    # The reported bug: "我是很高兴。对吗？" matched the 吗 keyword, so the
    # answer (and every Retry) explained 吗 instead of the real error.
    table = ai_client.ASSISTANT_OFFLINE[locale]
    issues = ai_client.ASSISTANT_SENTENCE_ISSUES[locale]
    reply = chat(client, asklearner, "我是很高兴。对吗？", locale)["reply"]
    assert issues["shi_adj"] in reply and "我很高兴" in reply, (locale, reply)
    assert table["ma"] not in reply, (locale, reply)
    assert_language(reply, locale)


def test_offline_does_not_invent_an_error_in_a_correct_sentence(client, asklearner):
    reply = chat(client, asklearner, "我很高兴。", "en")["reply"]
    assert ai_client.ASSISTANT_SENTENCE_ISSUES["en"]["intro"] not in reply, reply


def test_offline_finds_the_error_inside_an_english_question(client, asklearner):
    reply = chat(client, asklearner, "Why is 我是很高兴 wrong?", "en")["reply"]
    assert ai_client.ASSISTANT_SENTENCE_ISSUES["en"]["shi_adj"] in reply, reply


def test_the_model_is_told_what_the_grammar_checker_found(client, asklearner, model):
    chat(client, asklearner, "Why is 我是很高兴 wrong?", "ru")
    assert "grammar checker found" in system_prompt(model)
    assert ai_client.ASSISTANT_SENTENCE_ISSUES["en"]["shi_adj"] in system_prompt(model)
    chat(client, asklearner, "我很高兴", "ru")
    assert "grammar checker found" not in system_prompt(model)
