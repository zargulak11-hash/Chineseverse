"""
AI service abstraction.

Providers:
  - "gemini"  : Google Gemini API (REST generateContent via httpx; key/model
                from GEMINI_API_KEY / GEMINI_MODEL).
  - "offline" : deterministic, rule-based fallback so the whole product works
                with no API key configured.
"auto" picks Gemini when GEMINI_API_KEY is set, else offline.

Every function has an offline implementation, so LinguaVerse keeps working without
any external API key.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AIError(Exception):
    pass


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").lower())


def _contain(text: str, *keywords: str) -> bool:
    text = _normalize(text)
    return any(_normalize(k) and _normalize(k) in text for k in keywords)


def _active_provider() -> str:
    """"gemini" when a Gemini key is configured, otherwise "offline".

    Any provider value other than "offline" (including a stale "openai"
    left in an old .env) resolves the same way as "auto", so the app never
    tries to reach OpenAI.
    """
    if (settings.ai_provider or "auto").lower() == "offline":
        return "offline"
    return "gemini" if settings.gemini_api_key else "offline"


# ---------------------------------------------------------------------------
# Offline (rule-based) implementations
# ---------------------------------------------------------------------------


def _offline_transcribe(prompt: Optional[str], audio_hint: Optional[str] = None) -> str:
    """No ASR: use the client hint, or an empty transcript.

    The transcript is reconstructed from the audio chunk label the browser sends
    (browser-side Web Speech API) or, failing that, empty so keyword matching can
    still grade accurately against the expected keywords.
    """
    return (audio_hint or "").strip()


_CJK_CHAR = re.compile(r"[㐀-鿿]")


def _offline_evaluate(prompt: str, transcript: str, expected_keywords: List[str]) -> dict:
    """Deterministic grade from what the browser's speech recognizer heard.

    No audio model runs offline, so every score is derived from the
    transcript itself -- never randomized (these numbers feed Learning DNA):
      relevance      share of expected keywords present in the transcript
      pronunciation  share of the expected Chinese characters the recognizer
                     produced (it only outputs a character when it matched
                     that syllable, so this is a real, if coarse, proxy)
      tones          same signal, weighted more conservatively: a recognizer
                     can guess the right character from context despite a
                     wrong tone, so tone credit is capped lower
      fluency        how close the spoken length was to the expected length
      grammar        keyword coverage of a complete answer
    """
    keywords = [k for k in expected_keywords if _normalize(k)]
    tx = _normalize(transcript)
    if not tx:
        return {
            "pronunciation": 0.0, "tones": 0.0, "fluency": 0.0, "grammar": 0.0,
            "relevance": 0.0, "overall": 0.0,
            "feedback": "I couldn't hear anything. Check the microphone and try again.",
        }
    hits = [k for k in keywords if _normalize(k) in tx]
    relevance = (len(hits) / len(keywords) * 100.0) if keywords else 0.0

    expected_chars = set(_CJK_CHAR.findall("".join(keywords))) or set(_CJK_CHAR.findall(prompt or ""))
    heard_chars = _CJK_CHAR.findall(transcript)
    coverage = (len(expected_chars & set(heard_chars)) / len(expected_chars)) if expected_chars else relevance / 100
    pronunciation = 40.0 + 55.0 * coverage
    tones = 35.0 + 50.0 * coverage

    expected_len = max(len("".join(keywords)), 1)
    ratio = len(heard_chars) / expected_len if heard_chars else len(tx) / expected_len
    fluency = 45.0 + 45.0 * min(1.0, ratio) - (min(ratio - 2.5, 1.0) * 20.0 if ratio > 2.5 else 0.0)
    grammar = 45.0 + 0.5 * relevance

    overall = 0.35 * relevance + 0.25 * pronunciation + 0.2 * tones + 0.2 * fluency
    if relevance >= 90:
        feedback = "Perfect match. Keep that tone steady."
    elif relevance >= 55:
        feedback = "Good, but try speaking a little slower and clearer."
    else:
        feedback = "Listen once more and repeat the phrase; focus on the tones."
    return {
        "pronunciation": round(pronunciation, 1),
        "tones": round(tones, 1),
        "fluency": round(max(0.0, fluency), 1),
        "grammar": round(grammar, 1),
        "relevance": round(relevance, 1),
        "overall": round(overall, 1),
        "feedback": feedback,
    }


def _offline_react(transcript: str, expected_keywords: List[str], correct: str, incorrect: str) -> str:
    if _contain(transcript, *expected_keywords):
        return correct
    if not transcript:
        return "听不清，再说一遍好吗？"
    return incorrect


# ---------------------------------------------------------------------------
# Daily Voice Companion — Chinese-only content helpers.
#
# The animal's DB fields (Animal.name, .personality, .tone_style, and
# AnimalPersonality.catchphrase) are English, by design: they're shown as
# English/localized UI text elsewhere (the Companion page, the animal
# picker). The Daily Voice Companion is a dedicated Chinese-immersion
# screen, so its own spoken content must never splice those raw English
# strings in. These mappings are ChineseVerse-authored companion flavor
# text (not curriculum data), one per real animal, used ONLY by chat_reply/
# _offline_chat below -- they never touch the DB fields or any other page.
# ---------------------------------------------------------------------------

ANIMAL_ZH_NAME = {
    "panda": "熊猫", "red-panda": "小熊猫", "phoenix": "凤凰", "monkey": "猴子",
    "fox": "狐狸", "wolf": "狼", "snake": "蛇", "koala": "考拉",
    "cat": "猫", "dog": "狗", "tiger": "老虎", "rabbit": "兔子",
    "bird": "小鸟", "capybara": "水豚", "panther": "黑豹", "sheep": "绵羊",
    "elephant": "大象", "cow": "奶牛", "penguin": "企鹅", "owl": "猫头鹰",
}

# A short, natural Chinese line capturing the same vibe as the animal's
# English catchphrase (e.g. fox's "Wanna play a word game?" -> playful
# invitation to a word game), so personality still differs animal to
# animal without ever emitting the English original.
ANIMAL_ZH_FLAVOR = {
    "panda": "慢慢来，一步一步来。",
    "red-panda": "这个词是什么呀？",
    "phoenix": "每一次犯错，都是重新出发。",
    "fox": "要不要玩个词语游戏？",
    "wolf": "咱们可不能只做到一般水平。",
    "snake": "慢慢来，才能真正记住。",
    "cat": "呼噜～慢慢来，不着急。",
    "dog": "太棒了！再来一次！真厉害！",
    "tiger": "让我看看你的实力。",
    "rabbit": "摔倒了？跳起来，再试一次！",
    "bird": "声调对不对？再听一遍！",
    "capybara": "不急，慢慢来，继续吧。",
    "panther": "嗯……好像有点不对劲。",
    "sheep": "再来一次没关系，我们慢慢练。",
    "monkey": "嘿嘿！我们来点好玩的吧！",
    "koala": "嗯……慢慢来，抱一个。",
    "elephant": "大象不会忘记，你也不会。",
    "cow": "哞～一句一句慢慢来。",
    "penguin": "我们摇摇摆摆去聊天吧！",
    "owl": "咕咕！我们好好想一想。",
}

# Short Chinese personality description for the AI system prompt, replacing
# Animal.personality/tone_style (English) so nothing English ever appears
# in the prompt that shapes what the model says.
ANIMAL_ZH_PERSONALITY = {
    "panda": "温和、友善、让人安心",
    "red-panda": "好奇、有点害羞，对新词特别兴奋",
    "phoenix": "睿智、坚韧、说话有诗意",
    "fox": "聪明、机灵、有点调皮",
    "wolf": "忠诚、认真、专注目标",
    "snake": "沉稳、耐心、善于观察",
    "cat": "慵懒、独立、让人放松",
    "dog": "友好、忠诚、总是为你加油",
    "tiger": "强壮、有雄心、无所畏惧",
    "rabbit": "充满希望、可爱、坚韧不拔",
    "bird": "爱唱歌、好奇、话很多",
    "capybara": "淡定、平静、处变不惊",
    "panther": "神秘、善于分析、话不多",
    "sheep": "温柔、耐心、喜欢慢慢重复",
    "monkey": "调皮、好奇、爱开玩笑",
    "koala": "慵懒、温柔、让人想抱抱",
    "elephant": "睿智、沉稳、记忆力超强",
    "cow": "善良、耐心、踏实",
    "penguin": "友好、爱社交、开朗",
    "owl": "睿智、善于分析、好奇",
}

# Chinese feedback used ONLY by the Daily Voice Companion (see
# voice.py:submit_companion_chat) so the "{animal} says" coaching line is
# never the shared English feedback that /attempt and /evaluate still use
# for the main companion / World voice system.
_WEAKEST_LABEL_ZH = {"pronunciation": "发音", "tones": "声调", "fluency": "流利度", "grammar": "语法"}


def voice_companion_feedback_zh(scores: dict) -> str:
    """A short Chinese coaching line derived from the same score numbers the
    shared voice_eval pipeline already computed -- language-agnostic
    numbers in, Chinese-only text out, regardless of which provider (AI or
    offline) produced the scores."""
    overall = scores.get("overall", 0)
    sub = {k: scores.get(k, 0) for k in ("pronunciation", "tones", "fluency", "grammar")}
    weakest_key = min(sub, key=sub.get)
    weakest_zh = _WEAKEST_LABEL_ZH[weakest_key]
    if overall >= 85:
        return "非常好！继续保持这个状态！"
    if overall >= 65:
        return f"不错！{weakest_zh}再练一下会更好。"
    return f"再听一次，跟着慢慢说一遍，注意{weakest_zh}。"


def _offline_chat(
    messages: List[dict],
    animal_slug: str,
    user_name: str,
    energy: Optional[int] = None,
) -> str:
    """Deterministic, keyword-triggered, Chinese-only fallback. `energy` is
    the SAME per-animal AnimalPersonality field the real AI branch is told
    about -- so even offline, a high-energy animal like Cheetah doesn't
    read identically to a calm one like Capybara. The reply text is never
    prefixed with the animal's (English) name -- the frontend already shows
    that as a separate UI label; baking it into the message would itself be
    an English leak into the spoken content."""
    zh_name = ANIMAL_ZH_NAME.get(animal_slug, "朋友")
    flavor = ANIMAL_ZH_FLAVOR.get(animal_slug, "")
    last = messages[-1] if messages else {}
    content = (last.get("content") or "").lower()
    exclaim = "！" if (energy is None or energy >= 50) else "。"
    if _contain(content, "你好", "hi", "hello"):
        lead = f"{flavor} " if flavor else ""
        return f"{lead}你好{exclaim}我是{zh_name}，你的语言伙伴。你想聊什么？"
    if _contain(content, "名字", "name"):
        return f"我叫{zh_name}。你呢？你的中文名字是什么？"
    if _contain(content, "谢谢", "thank"):
        return f"不客气{exclaim}随时找我聊天。"
    if _contain(content, "再见", "bye", "拜拜"):
        tail = f" {flavor}" if flavor else ""
        return f"再见{exclaim}今天练习得不错。{tail}"
    return (
        f"我听到你说「{last.get('content', '')}」。"
        f"很有进步{exclaim}再说一遍怎么样？"
    )


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------


# Gemini models "think" before answering and those hidden tokens are counted
# against maxOutputTokens. On gemini-3.x the old `thinkingBudget: 0` switch
# is ignored (~200 thought tokens still spent) and `thinkingLevel: minimal`
# is rejected with a 400, so a 200-token cap returned two-word, MAX_TOKENS-
# truncated replies. Instead of model-specific thinking flags, each caller's
# max_tokens stays the size of the visible answer and this headroom is added
# on top for the thinking.
THINKING_HEADROOM = 2048

# Statuses that mean "this model can't answer right now, another might":
#   404  model retired -- how the assistant first broke: gemini-2.5-flash
#        became "no longer available to new users" and every request
#        silently fell back to offline;
#   429  quota -- free-tier keys get only ~20 requests/day PER MODEL on the
#        top Flash model, and quotas are counted per model;
#   5xx  "model is experiencing high demand" overloads, which are common.
# On these the call moves to the next model in GEMINI_FALLBACK_MODELS.
# Anything else -- 400 bad request, 401/403 bad key -- won't fix itself on
# another model, so it fails fast to the offline fallback.
_NEXT_MODEL = {404, 429, 500, 502, 503, 504}
_OVERLOADED = {500, 502, 503, 504}
_RETRY_DELAY_S = 1.5

# A model that answered 404 (retired) or 429 (quota spent -- the free-tier
# limit is per day) is skipped for a while instead of being asked first on
# every message: otherwise each chat paid an extra failed round trip per
# exhausted model before reaching one that still answers. In-process only;
# a restart simply tries every model again.
_MODEL_COOLDOWN_S = {404: 6 * 3600, 429: 15 * 60}
_cooling_until: dict[str, float] = {}


def _parts(m: dict) -> list[dict]:
    """A message's Gemini parts: its text, then any attachments the router
    already validated ({"mime": ..., "data": base64} for images/PDFs that
    the model reads itself; plain text files arrive already inlined)."""
    parts: list[dict] = []
    for a in m.get("attachments") or []:
        parts.append({"inline_data": {"mime_type": a["mime"], "data": a["data"]}})
    parts.append({"text": m["content"]})
    return parts


def _gemini_payload(
    messages: List[dict],
    max_tokens: int,
    temperature: float,
    json_mode: bool,
) -> dict:
    """Map the chat-style messages every caller builds ({role: system|user|
    assistant, content}) onto Gemini's generateContent body: system turns
    become systemInstruction, assistant turns become role "model"."""
    system = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
    contents = [
        {"role": "model" if m["role"] == "assistant" else "user", "parts": _parts(m)}
        for m in messages
        if m.get("role") in ("user", "assistant")
    ]
    config: dict = {"temperature": temperature, "maxOutputTokens": max_tokens + THINKING_HEADROOM}
    if json_mode:
        # The graders json.loads() the reply; without this Gemini tends to
        # wrap it in a ```json fence.
        config["responseMimeType"] = "application/json"
    body: dict = {"contents": contents, "generationConfig": config}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    return body


def _gemini_text(data: dict) -> str:
    try:
        candidate = data["candidates"][0]
        parts = candidate.get("content", {}).get("parts") or []
        # Skip thought-summary parts if a model ever returns them.
        content = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        # A blocked prompt comes back with no candidates at all. Every
        # caller already degrades to offline on ValueError.
        raise ValueError(f"Unexpected Gemini response shape: {type(exc).__name__}") from exc
    if not content.strip():
        # e.g. finishReason SAFETY / MAX_TOKENS with no text
        raise ValueError(f"Gemini returned no text (finishReason={candidate.get('finishReason')})")
    return content.strip()


def _gemini_chat(
    messages: List[dict],
    max_tokens: int = 200,
    temperature: float = 0.8,
    json_mode: bool = False,
) -> str:
    """One generateContent call. Tries GEMINI_MODEL, then each of
    GEMINI_FALLBACK_MODELS when a model is retired, out of quota or
    overloaded (one short retry on the first overload). Raises
    httpx.HTTPError / ValueError on failure -- every caller turns those into
    its offline fallback."""
    payload = _gemini_payload(messages, max_tokens, temperature, json_mode)
    base = settings.gemini_base_url.rstrip("/")
    models = list(dict.fromkeys([settings.gemini_model, *settings.gemini_fallback_models]))
    now = time.monotonic()
    # If every model is cooling down, try them all anyway rather than
    # giving up without asking.
    queue = [m for m in models if _cooling_until.get(m, 0) <= now] or models
    retried = False
    last_exc: Exception | None = None
    while queue:
        model = queue[0]
        try:
            resp = httpx.post(
                f"{base}/models/{model}:generateContent",
                # Key in a header, not the ?key= query string, so it can't
                # end up in URL logs or exception messages.
                headers={"x-goog-api-key": settings.gemini_api_key or ""},
                json=payload,
                # gemini-3.x replies took 7-14s in testing; 30s was too tight
                # once thinking is included.
                timeout=45,
            )
            resp.raise_for_status()
            _cooling_until.pop(model, None)
            return _gemini_text(resp.json())
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            status = exc.response.status_code
            # Log the status only -- never the request (it carries the key).
            logger.warning("Gemini %s returned HTTP %s", model, status)
            if status not in _NEXT_MODEL:
                raise
            if status in _MODEL_COOLDOWN_S:
                _cooling_until[model] = time.monotonic() + _MODEL_COOLDOWN_S[status]
            if status in _OVERLOADED and not retried:
                retried = True
                time.sleep(_RETRY_DELAY_S)
                continue  # same model once more
            queue.pop(0)
        except httpx.TimeoutException as exc:
            last_exc = exc
            logger.warning("Gemini %s timed out", model)
            queue.pop(0)
        except httpx.HTTPError as exc:
            logger.warning("Gemini unreachable: %s", type(exc).__name__)
            raise
    assert last_exc is not None
    raise last_exc


def _sse_text(line: str) -> str:
    """The visible text of one `data: {...}` line of a streamGenerateContent
    (alt=sse) response; thought parts and empty chunks give ""."""
    if not line.startswith("data:"):
        return ""
    try:
        data = json.loads(line[5:].strip())
        parts = data["candidates"][0].get("content", {}).get("parts") or []
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        return ""
    return "".join(p.get("text", "") for p in parts if not p.get("thought"))


def _gemini_stream(messages: List[dict], max_tokens: int = 1500, temperature: float = 0.7):
    """Stream one reply as text chunks (a generator).

    The same model fallback as _gemini_chat, but only BEFORE the first
    chunk: once text has reached the learner, switching models would splice
    two answers together, so a later failure raises instead. Closing the
    generator (the learner pressed Stop, or the browser went away) closes
    the HTTP stream, which cancels the request at Gemini too."""
    payload = _gemini_payload(messages, max_tokens, temperature, False)
    base = settings.gemini_base_url.rstrip("/")
    models = list(dict.fromkeys([settings.gemini_model, *settings.gemini_fallback_models]))
    now = time.monotonic()
    queue = [m for m in models if _cooling_until.get(m, 0) <= now] or models
    last_exc: Exception | None = None
    for model in queue:
        started = False
        try:
            with httpx.stream(
                "POST", f"{base}/models/{model}:streamGenerateContent",
                params={"alt": "sse"},
                headers={"x-goog-api-key": settings.gemini_api_key or ""},
                json=payload,
                timeout=httpx.Timeout(60, connect=10),
            ) as resp:
                if resp.status_code >= 400:
                    resp.read()
                    resp.raise_for_status()
                _cooling_until.pop(model, None)
                for line in resp.iter_lines():
                    text = _sse_text(line)
                    if text:
                        started = True
                        yield text
            if not started:
                raise ValueError("Gemini stream returned no text")
            return
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            status = exc.response.status_code
            logger.warning("Gemini %s stream returned HTTP %s", model, status)
            if status in _MODEL_COOLDOWN_S:
                _cooling_until[model] = time.monotonic() + _MODEL_COOLDOWN_S[status]
            if status not in _NEXT_MODEL:
                raise
        except (httpx.TimeoutException, ValueError) as exc:
            last_exc = exc
            logger.warning("Gemini %s stream failed: %s", model, type(exc).__name__)
            if started:
                raise
        except httpx.HTTPError as exc:
            logger.warning("Gemini unreachable: %s", type(exc).__name__)
            raise
    assert last_exc is not None
    raise last_exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def transcribe(prompt: Optional[str] = None, audio_hint: Optional[str] = None) -> str:
    """Return the learner's spoken Chinese as text."""
    return _offline_transcribe(prompt, audio_hint)


def evaluate_speech(
    prompt: str,
    transcript: str,
    expected_keywords: Optional[List[str]] = None,
) -> dict:
    """Grade a single spoken turn. Returns score dict (always complete)."""
    provider = _active_provider()
    expected_keywords = expected_keywords or []
    if provider == "gemini" and transcript:
        try:
            system = (
                "你是中文口语考官。根据提示、转录和关键词，返回JSON，"
                "包含 pronunciation/tones/fluency/grammar/relevance(0-100)、"
                "overall 和一句 feedback。"
            )
            user = (
                f"提示：{prompt}\n转录：{transcript}\n关键词：{expected_keywords}"
            )
            text = _gemini_chat(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                json_mode=True,
            )
            data = json.loads(text)
            return {
                "pronunciation": float(data.get("pronunciation", 0)),
                "tones": float(data.get("tones", 0)),
                "fluency": float(data.get("fluency", 0)),
                "grammar": float(data.get("grammar", 0)),
                "relevance": float(data.get("relevance", 0)),
                "overall": float(data.get("overall", 0)),
                "feedback": str(data.get("feedback", "Good attempt!")),
            }
        except (AIError, KeyError, ValueError, httpx.HTTPError) as exc:
            raise AIError(f"AI evaluation failed: {exc}") from exc
    return _offline_evaluate(prompt, transcript, expected_keywords)


CHINESE_ONLY_RULE = (
    "STRICT LANGUAGE RULE: Respond exclusively in Mandarin Chinese (simplified "
    "characters). Never output English, Russian, or Tajik. Never mix languages "
    "in the same reply. Do not translate your answer into the user's app UI "
    "language under any circumstance. Do not add pinyin or an English gloss "
    "next to the Chinese. This rule applies to every single turn of the "
    "conversation, not just the first message."
)


def chat_reply(
    messages: List[dict],
    animal_slug: str,
    user_name: str,
    energy: Optional[int] = None,
    level_hint: Optional[str] = None,
) -> str:
    """Daily Voice Companion reply -- this is a dedicated Chinese-immersion
    screen, so the returned text (and everything in the system prompt that
    could be echoed back) is Chinese-only, regardless of the app's UI
    language. `animal_slug` looks up the animal's Chinese name/flavor line/
    personality description (see ANIMAL_ZH_* above) -- the English
    Animal.name/personality/tone_style/AnimalPersonality.catchphrase fields
    (shared with the rest of the app) are deliberately never passed in
    here, only their Chinese counterparts. `level_hint`
    ("beginner"/"intermediate"/"advanced") reuses the learner's existing HSK
    level so the same animal adapts its Chinese instead of always talking
    at one fixed difficulty, while staying Chinese-only at every level.
    """
    # Fall back to a generic Chinese noun, never an English name, so an
    # animal added later without an ANIMAL_ZH_NAME entry still can't leak
    # English here.
    zh_name = ANIMAL_ZH_NAME.get(animal_slug, "朋友")
    zh_personality = ANIMAL_ZH_PERSONALITY.get(animal_slug, "")
    zh_flavor = ANIMAL_ZH_FLAVOR.get(animal_slug, "")

    provider = _active_provider()
    if provider == "gemini":
        try:
            level_line = {
                "beginner": "学习者是初级水平：用非常简单的中文、常用词汇，句子要短。",
                "intermediate": "学习者是中级水平：可以用更自然、稍复杂的中文对话，词汇更广。",
                "advanced": "学习者是高级水平：可以用丰富、自然、更复杂的中文和更有深度的问题。",
            }.get(level_hint or "", "")
            system = (
                f"{CHINESE_ONLY_RULE}\n\n"
                f"你是一个叫「{zh_name}」的中文语音伙伴。"
                + (f"你的性格：{zh_personality}。" if zh_personality else "")
                + (f"你说话的感觉类似「{zh_flavor}」这种语气，可以偶尔自然地用上这句话或类似的说法。" if zh_flavor else "")
                + "用符合你性格的语气和学习者说中文，引导对话，末尾给一句鼓励。"
                + "对话中不要用拼音解释，不要中英夹杂，直接说中文。"
                + (f" {level_line}" if level_line else "")
            )
            return _gemini_chat(
                [{"role": "system", "content": system}] + messages,
            )
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
            # Unreachable API, exhausted credits (429) or a malformed reply:
            # fall back to the deterministic offline companion, never a 500.
            pass
    return _offline_chat(messages, animal_slug, user_name, energy=energy)


TRANSLATE_LANGUAGE = {"en": "English", "ru": "Russian", "tg": "Tajik (Cyrillic script only)"}
# One Sentence lessons are re-opened and re-rendered; the same sentence in
# the same language never needs a second paid call. In-process and bounded.
_translation_cache: dict[tuple[str, str], str] = {}


def translate_sentence(text: str, locale: str) -> Optional[str]:
    """A natural translation of one Chinese sentence into the learner's UI
    language, or None when no AI provider answers (and for zh, where the
    sentence itself is the text). None is a real state, not an error: the
    lesson always shows the word-by-word gloss built from the curriculum's
    own meanings, so nothing is invented offline."""
    language = TRANSLATE_LANGUAGE.get(locale)
    if language is None or _active_provider() != "gemini":
        return None
    key = (text, locale)
    if key in _translation_cache:
        return _translation_cache[key]
    try:
        system = (
            f"Translate the Chinese sentence into {language}. Reply with the translation only: "
            "no quotes, no pinyin, no notes, one line."
        )
        out = _gemini_chat(
            [{"role": "system", "content": system}, {"role": "user", "content": text}],
            max_tokens=200, temperature=0.2,
        ).strip().strip('"“”')
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return None
    if locale == "tg":
        out = _tg_clean_mixed_script(out)
    if not out or _CJK_CHAR.search(out):
        return None
    if len(_translation_cache) > 500:
        _translation_cache.clear()
    _translation_cache[key] = out
    return out


EXPLAIN_LANGUAGE = {**TRANSLATE_LANGUAGE, "zh": "very simple Simplified Chinese"}
# How much a reading explanation may assume, by the learner's HSK level.
_EXPLAIN_DEPTH = (
    (2, "The learner is a beginner (HSK 1-2): use very short, plain sentences, at most 2 grammar points, "
        "no linguistic terms."),
    (4, "The learner is lower-intermediate (HSK 3-4): explain clearly, at most 3 grammar points, "
        "name a structure only with an example."),
    (6, "The learner is upper-intermediate (HSK 5-6): you may name structures and explain nuance, "
        "at most 4 points."),
    (9, "The learner is advanced (HSK 7-9): explain register, connotation, set phrases, idioms and how the "
        "sentence is built, at most 5 points."),
)


def explain_reading(text: str, locale: str, level: int, glossary: List[dict],
                    grammar: List[str]) -> Optional[dict]:
    """A learning explanation of one selected piece of Chinese from a story,
    or None when no AI provider answers (the reader then shows the
    curriculum's own word-by-word data, which is never invented).

    The model is given the curriculum's meanings for the words it will
    meet and told to rely on them: it explains the text in context -- what
    it means, how it is built, what is hard -- and must not state HSK
    levels, cite books or invent vocabulary. Its reply is validated field by
    field; anything malformed is dropped rather than shown."""
    language = EXPLAIN_LANGUAGE.get(locale)
    if language is None or _active_provider() != "gemini":
        return None
    depth = next(d for top, d in _EXPLAIN_DEPTH if level <= top)
    gloss = "\n".join(f"{g['text']} ({g.get('pinyin') or ''}): {g.get('meaning') or ''}" for g in glossary[:40])
    system = (
        "You are a Chinese reading tutor inside a language-learning app. Explain ONLY the selected Chinese text "
        f"to the learner, in {language}. {depth} "
        "Rely on the dictionary glosses provided for word meanings; never invent meanings, never mention HSK "
        "levels, textbooks, sources or citations. If something is uncertain, leave it out. "
        "Reply as JSON with exactly these keys: "
        '"translation" (a natural translation of the selected text), '
        '"meaning" (one or two sentences: what the text says in its context), '
        '"points" (a list of {"title": short label, "body": explanation} about grammar, word usage or anything '
        'difficult in this text), '
        '"example" ({"zh": one new short Chinese sentence using the main point, "translation": its translation}, '
        "or null)."
        + (' For a Chinese-language learner interface, "translation" is null.' if locale == "zh" else "")
    )
    user = f"Selected text: {text}\nDictionary glosses:\n{gloss or '-'}"
    if grammar:
        user += "\nGrammar points the app recognises in it: " + "; ".join(grammar[:6])
    try:
        raw = _gemini_chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=900, temperature=0.3, json_mode=True,
        )
        data = json.loads(raw)
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None

    def clean(v, limit):
        if not isinstance(v, str):
            return None
        v = v.strip()
        if locale == "tg":
            v = _tg_clean_mixed_script(v)
        return v[:limit] or None

    out = {"translation": None if locale == "zh" else clean(data.get("translation"), 600),
           "meaning": clean(data.get("meaning"), 600), "points": [], "example": None}
    if out["translation"] and _CJK_CHAR.search(out["translation"]):
        out["translation"] = None
    for p in (data.get("points") or [])[:5]:
        if isinstance(p, dict):
            title, body = clean(p.get("title"), 120), clean(p.get("body"), 700)
            if title and body:
                out["points"].append({"title": title, "body": body})
    ex = data.get("example")
    if isinstance(ex, dict):
        zh = ex.get("zh") if isinstance(ex.get("zh"), str) else ""
        if _CJK_CHAR.search(zh) and len(zh) <= 80:
            out["example"] = {"zh": zh.strip(), "translation": None if locale == "zh" else clean(ex.get("translation"), 300)}
    if not (out["meaning"] or out["points"] or out["translation"]):
        return None
    return out


def grammar_lesson(title: str, pattern: str, examples: List[str], locale: str, level: int) -> Optional[dict]:
    """A full textbook-style lesson on one syllabus grammar point, in the
    learner's language, as JSON in the same shape as the authored lessons
    (seed_content/grammar/*.json). Returns the raw dict for
    grammar_lesson.validate_ai_lesson to clean, or None with no model.

    Pinyin is deliberately not asked for: the app computes it from the
    curriculum, so a model can't put a wrong reading on a page."""
    language = EXPLAIN_LANGUAGE.get(locale)
    if language is None or _active_provider() != "gemini":
        return None
    depth = next(d for top, d in _EXPLAIN_DEPTH if level <= top)
    tr_rule = ('"tr": null' if locale == "zh" else f'"tr": a natural {language} translation')
    system = (
        "You are an experienced Mandarin teacher writing one page of a digital grammar textbook. "
        f"Write every explanation in {language}; all Chinese is Simplified Chinese. {depth} "
        f"{_GRAMMAR_FACTS} "
        "Every Chinese sentence you write must be natural, correct Mandarin that a native teacher would use; "
        "keep example sentences short (under 25 characters) and use common words. Never mention HSK levels, "
        "textbooks or sources. Reply as JSON with exactly these keys:\n"
        '"name": a short friendly name of the grammar point;\n'
        '"summary": one or two sentences: what it means and does;\n'
        '"structure": 1-3 items {"formula": the sentence structure with the slots named in the explanation '
        'language, e.g. "Subject + 很 + Adjective", "zh": one example sentence};\n'
        '"when_to_use": 2-4 short points; "when_not": 1-3 short points (when NOT to use it, typical confusion);\n'
        '"explanation": 2-4 short paragraphs for a learner, plain language;\n'
        '"deeper": 0-2 short paragraphs of nuance for stronger learners (may be empty);\n'
        f'"examples": 5-6 items {{"zh", {tr_rule}, "note": a few words on what to notice or null}};\n'
        f'"negative": 0-2 items {{"zh", "tr"}} showing the negative form when it exists;\n'
        f'"questions": 0-2 items {{"zh", "tr"}} showing the question form when it exists;\n'
        '"mistakes": 2-3 typical learner mistakes {"wrong": incorrect Chinese, "right": the corrected Chinese, '
        '"why": short reason};\n'
        '"similar": 0-3 {"pattern": a similar pattern, "difference": how it differs};\n'
        f'"dialogue": 2-4 lines {{"speaker": "A" or "B", "zh", "tr"}} of a short real-life exchange using the point;\n'
        '"register": one sentence on formal vs spoken use, or null;\n'
        '"vocabulary": 3-8 key Chinese words the examples use;\n'
        '"exercises": 2-3 items, either {"type": "choose", "prompt": instruction, "options": 2-4 Chinese '
        'sentences, "answer": index of the ONLY correct one, "why": short reason} or {"type": "write", '
        '"prompt": what to write (e.g. a sentence to translate), "answer": the Chinese answer}.'
    )
    user = f"Grammar point: {title}\nPattern: {pattern or '-'}"
    if examples:
        user += "\nSyllabus examples:\n" + "\n".join(examples[:8])
    try:
        raw = _gemini_chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=3500, temperature=0.3, json_mode=True,
        )
        data = json.loads(raw)
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return None
    if locale == "tg" and isinstance(data, dict):
        data = json.loads(_tg_clean_mixed_script(json.dumps(data, ensure_ascii=False)))
    return data if isinstance(data, dict) else None


def evaluation_fallback(prompt: str, transcript: str, expected_keywords: Optional[List[str]] = None) -> dict:
    """Graceful degradation when the live AI call fails mid-flight."""
    return _offline_evaluate(prompt, transcript, expected_keywords or [])


def evaluate_case_solution(
    case_context: str,
    conclusion: str,
    solution_keywords: List[str],
    hint: str = "",
) -> dict:
    """Grade a Chinese Cases verdict.

    With a live AI key this actually reasons about whether the player's
    free-text conclusion matches the case's solution, instead of only
    checking whether a magic keyword substring appears somewhere in it.
    Always falls back to the deterministic keyword check so cases still
    work with no API key configured.
    """
    provider = _active_provider()
    if provider == "gemini" and conclusion:
        try:
            system = (
                "你是中文侦探解谜游戏的裁判。根据案情背景、正确答案的关键线索和玩家的结论，"
                "判断玩家是否正确破案（不要求逐字匹配，只要结论的意思正确）。"
                '返回JSON，格式为 {"solved": true 或 false, "feedback": "一句简短反馈"}。'
            )
            user = (
                f"案情：{case_context}\n关键线索：{solution_keywords}\n提示：{hint}\n"
                f"玩家的结论：{conclusion}"
            )
            text = _gemini_chat(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                json_mode=True,
            )
            data = json.loads(text)
            return {
                "solved": bool(data.get("solved")),
                "feedback": str(data.get("feedback") or ""),
            }
        except (KeyError, ValueError, httpx.HTTPError):
            pass  # fall through to the deterministic check below
    solved = _contain(conclusion, *solution_keywords)
    return {"solved": solved, "feedback": ""}


# ---------------------------------------------------------------------------
# In-app study assistant — a real conversational assistant that knows it
# lives inside ChineseVerse. Reuses the same provider plumbing as everything
# else in this module (chat_reply, evaluate_speech, ...) instead of a
# separate AI integration.
#
# It used to be told to "ONLY help with" the app and to decline anything
# else, and the offline fallback ended in a keyword matcher whose catch-all
# was that same refusal. With the configured key out of credits every
# request silently landed there, so "Салом" or "what should I see in China?"
# got "I can only help with ChineseVerse..." -- the assistant looked broken.
# Now the model answers whatever is asked, the learner's real stats are
# context rather than a script, and the offline path says plainly that the
# AI is unavailable instead of pretending the question was off-topic.
# ---------------------------------------------------------------------------

ASSISTANT_SYSTEM_TEMPLATE = (
    "REPLY LANGUAGE: {language}.{language_detail}\n\n"
    "You are the ChineseVerse assistant, built into ChineseVerse, a gamified "
    "app for learning Mandarin Chinese (HSK 1-9 roadmap, lessons, vocabulary, "
    "Hanzi, grammar, server-graded practice, spaced-repetition Review, "
    "Learning Compass skill profile, companions, Daily Voice Companion, Duels, "
    "Missions, Quests, Pet Teacher mode, streaks, XP and coins).\n\n"
    "The nine-skill profile is called {compass} in the app (it used to be "
    "called \"DNA\"); always use that name.\n\n"
    "Your role: a patient, expert Chinese teacher and the learner's guide to "
    "ChineseVerse.\n"
    "- Chinese questions (grammar, words, characters, pronunciation and tones, "
    "reading, HSK, study plans, culture) are your core job: answer them fully "
    "and correctly. For a grammar or usage question, teach it: meaning -> "
    "structure -> an example with pinyin -> a word-by-word breakdown -> why it "
    "works -> a common mistake (wrong vs right) -> one or two more examples -> "
    "a tiny practice question. Skip steps that don't help a simple question; "
    "never pad. Adapt to the learner's level below: plain words and short "
    "sentences for HSK 1-2, more nuance and terminology for higher levels.\n"
    "- Be correct about Mandarin: adjectives are predicates on their own (我很高兴。 "
    "is right and needs no 是); 是 links nouns; 有 is negated with 没. If you "
    "are not sure about something, say so rather than guess.\n"
    "- Questions about ChineseVerse itself or the learner's progress: answer "
    "from the learner data and page context below. It is the ONLY data you have "
    "about them: never invent scores, streaks, mastered words, completed "
    "lessons, Learning Compass numbers or achievements; if something isn't "
    "listed, say you don't have it. Only mention app features named in this "
    "prompt.\n"
    "- You have no internet access, no web search and no live data (weather, "
    "news, prices, schedules): never claim to have looked anything up, and "
    "never pretend ChineseVerse has a feature it doesn't. For such requests say "
    "so briefly and offer something useful in Chinese instead (for example the "
    "words to ask about the weather in Chinese).\n"
    "- Unrelated topics: greetings and small talk are welcome. For other "
    "unrelated questions give at most a short, careful answer, note kindly that "
    "you are focused on Chinese learning, and offer a Chinese angle. Do not "
    "refuse rudely.\n"
    "- Images and files the learner attaches are part of the question: read "
    "them carefully (a textbook page, a sign, handwriting) and say exactly "
    "what you see; if something is unreadable, say so.\n"
    "- You are read-only: you cannot change progress, XP, streaks, mastery or "
    "lessons, and must never claim you did. Progress only changes when the "
    "learner practises in the app.\n"
    "- Formatting: short paragraphs, '* ' bullet lines, **bold** and lines "
    "starting with '### ' as section titles (the chat renders just these); no "
    "tables or code blocks. Put pinyin in parentheses after Chinese.\n\n"
    "Learner data (from the ChineseVerse database):\n{learner}\n\n"
    "LANGUAGE: always reply in {language} -- the language this learner selected "
    "in the app -- even if they write to you in another language. Chinese "
    "examples (characters, pinyin) stay in Chinese; everything else is {language}."
    "{language_detail}"
)

# The app's selected UI language (X-Locale) decides the assistant's reply
# language, the same way it localizes every other screen. Names are written
# in English because they go into the English system prompt above.
ASSISTANT_LANGUAGE_NAMES = {"en": "English", "ru": "Russian", "tg": "Tajik", "zh": "Simplified Chinese"}

# A bare "Tajik" wasn't enough: with TG selected and a question typed in
# English, gemini-flash-lite answered in Uzbek written in Latin script
# ("Sun'iy intellekt ... bu kompyuter tizimlari ..."). Tajik is also easy to
# confuse with Russian (same Cyrillic base) and with Persian (same language
# family, Arabic script), so the TG rule names the script and the letters
# that only Tajik Cyrillic has, and rules the look-alikes out. The rule is
# stated at the top and again at the end of the prompt, since lighter
# fallback models weigh the opening instruction most.
# The skill profile's product name in the reply language only -- naming
# the other languages here would pull lighter models off the reply language.
ASSISTANT_COMPASS_NAME = {
    "en": "the Learning Compass",
    "ru": "\"Компас обучения\"",
    "tg": "\"Қутбнамои омӯзиш\"",
    "zh": "\"学习指南针\"",
}

ASSISTANT_LANGUAGE_DETAIL = {
    "tg": (
        " Write in Tajik (тоҷикӣ), the official language of Tajikistan, in the "
        "Tajik Cyrillic alphabet, using its own letters ғ, ӣ, қ, ӯ, ҳ, ҷ where "
        "Tajik spelling needs them (e.g. «ҳа», «бо ҷонам», «забони чинӣ»). Do NOT "
        "answer in Russian, Uzbek, Persian/Farsi or Dari, and never use Latin or "
        "Arabic script for the answer -- even when the learner writes in "
        "Russian, English or another language."
    ),
    "ru": " Write in Russian (Cyrillic), even if the learner writes in another language.",
    "zh": " Write in Simplified Chinese characters (简体中文), not Traditional.",
}

# Even with that rule, the lighter fallback model now and then emits a
# single foreign letter INSIDE an otherwise Cyrillic Tajik word -- seen
# live: «Бо کмоли» (Arabic kaf for к), «супуrтани» (Latin r for р). Only such
# mixed-script words are touched, letter by letter; whole Latin words
# (ChineseVerse, HSK, pinyin such as Běijīng) and Chinese stay as they are,
# so the model's answer itself is never rewritten.
_TG_LATIN = dict(zip("abcdefghijklmnopqrstuvwxyz", "абсдефгҳиҷклмнопқрстуввхйз"))
_TG_ARABIC = {
    "ا": "а", "ب": "б", "پ": "п", "ت": "т", "ج": "ҷ", "چ": "ч", "ح": "ҳ", "خ": "х",
    "د": "д", "ر": "р", "ز": "з", "ژ": "ж", "س": "с", "ش": "ш", "ع": "ъ", "غ": "ғ",
    "ف": "ф", "ق": "қ", "ک": "к", "ك": "к", "گ": "г", "ل": "л", "م": "м", "ن": "н",
    "و": "в", "ه": "ҳ", "ی": "и", "ي": "и",
}
_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")
_FOREIGN_RE = re.compile(r"[A-Za-z؀-ۿ]")
_WORD_RE = re.compile(r"[\w؀-ۿ]+")


def _tg_clean_mixed_script(text: str) -> str:
    def fix(match: re.Match) -> str:
        word = match.group(0)
        if not (_CYRILLIC_RE.search(word) and _FOREIGN_RE.search(word)):
            return word
        out = []
        for ch in word:
            low = ch.lower()
            if low in _TG_LATIN:
                rep = _TG_LATIN[low]
                out.append(rep.upper() if ch.isupper() else rep)
            else:
                out.append(_TG_ARABIC.get(ch, ch))
        return "".join(out)

    return _WORD_RE.sub(fix, text)


def _learner_block(context: dict) -> str:
    """Only facts the router actually read from the database go in; a
    missing value is omitted rather than defaulted, so the model can't
    present a placeholder as the learner's real data."""
    lines = []
    if context.get("username"):
        lines.append(f"- username: {context['username']}")
    if context.get("hsk_level") is not None:
        lines.append(f"- current HSK level on the lesson path: {context['hsk_level']}")
    if context.get("current_lesson"):
        lines.append(
            f"- current lesson on the lesson path: \"{context['current_lesson']}\""
            f" (HSK {context.get('current_lesson_level')})"
        )
    if context.get("pending_exam_level") is not None:
        lines.append(
            f"- all HSK {context['pending_exam_level']} lessons are done; the next step is the"
            f" HSK {context['pending_exam_level']} final exam (Lessons page), which must be passed"
            " before the next level opens"
        )
    if context.get("exams_passed"):
        lines.append("- HSK final exams passed: " + ", ".join(f"HSK {n}" for n in context["exams_passed"]))
    if context.get("mastery") is not None:
        lines.append(f"- overall mastery at that level: {context['mastery']}%")
    if context.get("streak") is not None:
        lines.append(f"- current study streak: {context['streak']} day(s)")
    if context.get("due_reviews") is not None:
        lines.append(f"- items due in Review now: {context['due_reviews']}")
    if context.get("open_mistakes") is not None:
        lines.append(f"- unresolved mistakes in the mistake bank: {context['open_mistakes']}")
    if context.get("recent_mistakes"):
        lines.append("- most recent mistakes: " + "; ".join(context["recent_mistakes"]))
    if context.get("dna_overall") is not None:
        lines.append(f"- Learning Compass overall: {context['dna_overall']}%")
    if context.get("skill_mastery"):
        lines.append("- Learning Compass skill mastery: " + ", ".join(context["skill_mastery"]))
    if context.get("weak_skills"):
        lines.append("- weakest Learning Compass skills: " + ", ".join(context["weak_skills"]))
    else:
        lines.append("- weakest Learning Compass skills: not enough practice yet to tell")
    if context.get("words_mastered") is not None:
        lines.append(f"- vocabulary words mastered: {context['words_mastered']}")
    if context.get("completed_lessons") is not None:
        lines.append(f"- lessons completed: {context['completed_lessons']}")
    lines.append(f"- main companion: {context.get('companion') or 'none chosen yet'}")
    if context.get("today"):
        lines.append("- today's plan in the app: " + context["today"])
    if context.get("page"):
        lines.append("\nWhat the learner has open right now (answer about this when they say \"this\"):\n"
                     + context["page"])
    return "\n".join(lines)


# Offline replies, one set per supported app locale; "en" is the fallback for
# any unknown locale. Used ONLY when no live model is configured or the call
# failed, so every reply opens with an honest "AI is unavailable" notice and
# then gives the most useful thing a deterministic helper can: a grounded
# answer for a few common questions, or the learner's own next step from
# real data. Chinese examples (了/吗/的 sentences) are the subject being
# taught, so they stay Chinese in every set.
ASSISTANT_OFFLINE = {
    "en": {
        "unavailable": "The AI assistant is temporarily unavailable, so this is a short automatic answer.",
        "greet": "Hi {name}! Once the AI is back you can ask me anything — about Chinese or anything else.",
        "default_name": "there",
        "level": (
            "You're at HSK {hsk_level} with {mastery}% overall mastery. "
            "Keep reviewing Vocabulary and Lessons daily — the HSK Roadmap page shows exactly "
            "what's left to unlock the next level."
        ),
        "streak": (
            "Your current streak is {streak} day(s). Do at least one review, lesson "
            "or conversation today to keep it alive."
        ),
        "weak": (
            "Your weakest skill right now looks like {weak}. A Mission or Duel that targets it "
            "is the fastest way to move the needle — check your Learning Compass for the exact numbers."
        ),
        "no_weak": "a bit of everything so far",
        "le": (
            "了 (le) usually marks a completed action or a change of state — e.g. 我吃了 (I ate) "
            "vs 我在吃 (I'm eating). Try it in a Lesson or a Pet Teacher case to see it corrected live."
        ),
        "ma": "吗 (ma) turns a statement into a yes/no question — 你好吗？ = \"Are you well?\" Just add it to the end of a sentence.",
        "de": "的 (de) is the all-purpose possessive/descriptive particle — 我的书 = \"my book\". It links a modifier to the noun after it.",
        "xp": "You earn XP and coins from voice attempts, quests, missions and duels — the Quests page usually has today's easiest wins.",
        "companion": "Your companion is {companion}. Each one biases your daily quests and missions toward its own specialty — see the Companion page.",
        "no_companion": "no companion chosen yet",
        "duel": "A duel is 1-vs-1 with another learner: you both get the same questions and your own clock. Challenge someone from the Duels page — every answer still counts as practice.",
        "general": (
            "Please try your question again in a little while. Meanwhile, your next step: "
            "you're at HSK {hsk_level} and have {due} item(s) waiting in Review."
        ),
    },
    "ru": {
        "unavailable": "ИИ-ассистент временно недоступен, поэтому это короткий автоматический ответ.",
        "greet": "Привет, {name}! Когда ИИ снова заработает, можешь спросить меня о чём угодно — о китайском и не только.",
        "default_name": "друг",
        "level": (
            "Ты на уровне HSK {hsk_level}, общее освоение — {mastery}%. "
            "Повторяй словарь и уроки каждый день — на странице плана HSK видно, "
            "что осталось до следующего уровня."
        ),
        "streak": (
            "Твоя текущая серия — {streak} дн. Сделай сегодня хотя бы одно повторение, урок "
            "или разговор, чтобы её сохранить."
        ),
        "weak": (
            "Сейчас твой самый слабый навык — {weak}. Миссия или дуэль на этот навык — "
            "самый быстрый способ его подтянуть. Точные цифры — в компасе обучения."
        ),
        "no_weak": "пока понемногу всё",
        "le": (
            "了 (le) обычно обозначает завершённое действие или изменение состояния — например, 我吃了 (я поел) "
            "и 我在吃 (я ем). Попробуй его в уроке или в режиме Pet Teacher, чтобы сразу увидеть исправления."
        ),
        "ma": "吗 (ma) превращает утверждение в вопрос «да/нет» — 你好吗？ = «Как дела?» Просто добавь его в конец предложения.",
        "de": "的 (de) — универсальная частица принадлежности и определения — 我的书 = «моя книга». Она связывает определение с существительным после него.",
        "xp": "Опыт и монеты даются за голосовые попытки, квесты, миссии и дуэли — на странице квестов обычно есть самые лёгкие задания на сегодня.",
        "companion": "Твой компаньон — {companion}. Каждый компаньон смещает ежедневные квесты и миссии в сторону своей специализации — загляни на страницу компаньона.",
        "no_companion": "компаньон пока не выбран",
        "duel": "Дуэль — это один на один с другим учеником: у вас одинаковые вопросы и у каждого свой таймер. Вызови кого-нибудь на странице дуэлей — каждый ответ всё равно засчитывается как практика.",
        "general": (
            "Попробуй задать вопрос ещё раз чуть позже. А пока следующий шаг: "
            "ты на уровне HSK {hsk_level}, в повторении ждут элементов: {due}."
        ),
    },
    "tg": {
        "unavailable": "Ёрдамчии зеҳни сунъӣ муваққатан дастнорас аст, бинобар ин ин ҷавоби кӯтоҳи худкор аст.",
        "greet": "Салом, {name}! Вақте ки зеҳни сунъӣ дубора кор кунад, метавонед аз ман ҳар чиз пурсед — дар бораи забони чинӣ ва на танҳо.",
        "default_name": "дӯст",
        "level": (
            "Шумо дар сатҳи HSK {hsk_level} ҳастед, азхудкунии умумӣ {mastery}% аст. "
            "Луғат ва дарсҳоро ҳар рӯз такрор кунед — саҳифаи нақшаи HSK нишон медиҳад, "
            "ки то сатҳи навбатӣ чӣ боқӣ мондааст."
        ),
        "streak": (
            "Силсилаи ҳозираи шумо {streak} рӯз аст. Барои нигоҳ доштани он имрӯз ақаллан як такрор, "
            "дарс ё гуфтугӯ анҷом диҳед."
        ),
        "weak": (
            "Ҳоло заифтарин маҳорати шумо {weak} аст. Миссия ё дуэл барои ҳамин маҳорат "
            "роҳи зудтарини беҳтар кардани он аст — рақамҳои дақиқ дар қутбнамои омӯзиш."
        ),
        "no_weak": "ҳоло ҳамааш каме-каме",
        "le": (
            "了 (le) одатан амали анҷомёфта ё тағйири ҳолатро нишон медиҳад — масалан, 我吃了 (ман хӯрдам) "
            "ва 我在吃 (ман хӯрда истодаам). Онро дар дарс ё дар реҷаи Pet Teacher санҷед, то ислоҳро фавран бинед."
        ),
        "ma": "吗 (ma) ҷумларо ба саволи «ҳа/не» табдил медиҳад — 你好吗？ = «Аҳволатон чӣ хел?» Танҳо онро ба охири ҷумла илова кунед.",
        "de": "的 (de) ҳиссачаи умумии тааллуқ ва тавсиф аст — 我的书 = «китоби ман». Он муайянкунандаро бо исми баъдӣ мепайвандад.",
        "xp": "Таҷриба ва тангаҳоро барои кӯшишҳои овозӣ, супоришҳо, миссияҳо ва дуэлҳо мегиред — дар саҳифаи супоришҳо одатан осонтарин вазифаҳои имрӯза ҳастанд.",
        "companion": "Ҳамроҳи шумо — {companion}. Ҳар ҳамроҳ супоришҳо ва миссияҳои ҳаррӯзаро ба самти тахассуси худ майл медиҳад — саҳифаи ҳамроҳро бинед.",
        "no_companion": "ҳамроҳ ҳоло интихоб нашудааст",
        "duel": "Дуэл бозии як ба як бо омӯзандаи дигар аст: саволҳо якхелаанд ва ҳар кас вақти худро дорад. Касеро аз саҳифаи дуэлҳо даъват кунед — ҳар ҷавоб ҳамчун машқ ҳисоб мешавад.",
        "general": (
            "Лутфан саволатонро каме баъдтар боз диҳед. Ҳоло қадами навбатӣ: "
            "шумо дар сатҳи HSK {hsk_level} ҳастед ва дар такрор {due} унсур интизор аст."
        ),
    },
    "zh": {
        "unavailable": "AI 助手暂时无法使用，下面是一条简短的自动回复。",
        "greet": "你好，{name}！AI 恢复后，你可以问我任何问题——中文学习或其他话题都可以。",
        "default_name": "同学",
        "level": (
            "你现在是 HSK {hsk_level}，总体掌握度 {mastery}%。"
            "每天坚持复习词汇和课程——HSK 学习计划页面会清楚显示离下一级还差什么。"
        ),
        "streak": "你目前已连续学习 {streak} 天。今天至少完成一次复习、一节课或一次对话，保持连续记录。",
        "weak": "你目前最薄弱的技能是{weak}。针对它的任务或对战是提升最快的方法——具体数据请看学习指南针。",
        "no_weak": "目前各方面都还在起步",
        "le": "了 (le) 通常表示动作完成或状态变化——例如 我吃了（已经吃过）和 我在吃（正在吃）。可以在课程或 Pet Teacher 案例中试一试，马上看到纠正。",
        "ma": "吗 (ma) 能把陈述句变成是非疑问句——你好吗？ 只要把它放在句末就可以。",
        "de": "的 (de) 是最常用的结构助词，表示所属或修饰——我的书 就是“属于我的书”。它把修饰语和后面的名词连接起来。",
        "xp": "语音练习、任务、使命和对战都能获得经验值和金币——任务页面通常有今天最容易完成的奖励。",
        "companion": "你的伙伴是{companion}。每个伙伴都会让每日任务和使命偏向它的专长——请查看伙伴页面。",
        "no_companion": "还没有选择伙伴",
        "duel": "对决是与另一位学习者一对一：题目相同，各自计时。在对决页面挑战别人吧——每个回答都算作练习。",
        "general": "请稍后再问一次。现在的下一步：你是 HSK {hsk_level}，复习中有 {due} 项等着你。",
    },
}

# Topic keywords in every supported language: the learner may type in any of
# them, but the REPLY language is always the selected locale.
_KW_GREET = ("hello", "hi", "hey", "привет", "здравств", "салом", "你好", "您好")
_KW_LEVEL = ("hsk", "level", "progress", "уровень", "прогресс", "сатҳ", "пешрафт", "水平", "进度", "等级", "级别")
_KW_STREAK = ("streak", "серия", "стрик", "силсила", "连续", "打卡")
_KW_WEAK = ("weak", "improve", "focus", "struggl", "слаб", "улучш", "заиф", "беҳтар", "薄弱", "弱", "提高", "加强")
_KW_XP = ("xp", "coin", "reward", "опыт", "монет", "наград", "таҷриба", "танга", "мукофот", "经验", "金币", "奖励")
_KW_COMPANION = ("companion", "animal", "компаньон", "животн", "питом", "ҳамроҳ", "ҳайвон", "伙伴", "动物", "宠物")
_KW_DUEL = ("duel", "дуэл", "поедин", "对战", "决斗")


def _is_greeting(text: str) -> bool:
    # Whole-word match for the short Latin greetings ("hi" is inside "this").
    words = re.findall(r"\w+", (text or "").lower())
    if len(words) > 4:
        return False
    return any(w in _KW_GREET for w in words) or _contain(text, "привет", "здравств", "салом", "你好", "您好")


def _offline_answer(last: str, context: dict, t: dict) -> str:
    q = _normalize(last)
    name = context.get("username") or t["default_name"]
    if not q or _is_greeting(last):
        return t["greet"].format(name=name)
    if _contain(q, *_KW_LEVEL):
        return t["level"].format(hsk_level=context.get("hsk_level", 1), mastery=context.get("mastery", 0))
    if _contain(q, *_KW_STREAK):
        return t["streak"].format(streak=context.get("streak", 0))
    if _contain(q, *_KW_WEAK):
        weak = ", ".join(context.get("weak_skills") or []) or t["no_weak"]
        return t["weak"].format(weak=weak)
    if "了" in last:
        return t["le"]
    if "吗" in last:
        return t["ma"]
    if "的" in last:
        return t["de"]
    if _contain(q, *_KW_XP):
        return t["xp"]
    if _contain(q, *_KW_COMPANION):
        return t["companion"].format(companion=context.get("companion") or t["no_companion"])
    if _contain(q, *_KW_DUEL):
        return t["duel"]
    return t["general"].format(hsk_level=context.get("hsk_level", 1), due=context.get("due_reviews", 0))


def _offline_assistant_reply(messages: List[dict], context: dict, locale: str = "en") -> str:
    t = ASSISTANT_OFFLINE.get(locale, ASSISTANT_OFFLINE["en"])
    last = messages[-1]["content"] if messages else ""
    return f"{t['unavailable']}\n\n{_offline_answer(last, context, t)}"


def assistant_reply(messages: List[dict], context: dict, locale: str = "en") -> tuple[str, str]:
    """Reply to one turn of the in-app assistant. Returns (reply, source),
    where source is "ai" for a real model answer or "offline" for the
    fallback. `context` carries the learner's own stats as read from the
    database, so answers about "how am I doing" are grounded in real data,
    not hallucinated. `locale` is the app's selected language (X-Locale);
    both the model and the offline fallback answer in it."""
    if _active_provider() == "gemini" and messages:
        try:
            reply = _gemini_chat(
                [{"role": "system", "content": _assistant_system(context, locale)}] + messages,
                max_tokens=1500,
                temperature=0.6,
            )
            if locale == "tg":
                reply = _tg_clean_mixed_script(reply)
            return reply, "ai"
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
            # Unreachable API, exhausted credits (429) or a malformed reply:
            # degrade to the offline helper, never a 500.
            pass
    return _offline_assistant_reply(messages, context, locale), "offline"


# Facts every Chinese grader is reminded of. The old Pet Teacher prompt gave
# the model only the rule; with no sentence in front of it, it answered a
# correct 我很高兴。 with a lecture about why 是 "is needed" -- the opposite
# of the rule. Stating the core facts and the verdict the rules already
# reached keeps a model from contradicting them.
_GRAMMAR_FACTS = (
    "Facts about Mandarin you must respect: adjectives are predicates on their own, so "
    "我很高兴。 我很累。 她很漂亮。 天气很好。 are correct and need no 是; 很 before an "
    "adjective predicate is normal and often only marks it as a statement. 是 links a subject to "
    "a NOUN (我是学生。). Punctuation differences and a missing final 。 are never errors. "
    "Never call a correct sentence wrong."
)
JUDGE_CATEGORIES = ("correct", "alternative", "unnatural", "typo", "grammar", "vocabulary", "different")


def _language_rule(locale: str) -> str:
    name = ASSISTANT_LANGUAGE_NAMES.get(locale, "English")
    return f"Write all feedback in {name}.{ASSISTANT_LANGUAGE_DETAIL.get(locale, '')} Chinese examples stay in Chinese."


def _clean_feedback(text, locale: str, limit: int = 400) -> str:
    if not isinstance(text, str):
        return ""
    text = text.strip()
    if locale == "tg":
        text = _tg_clean_mixed_script(text)
    return text[:limit]


def judge_sentence(answer: str, expected: str, task: str, locale: str = "en",
                   wrong: str = "") -> Optional[dict]:
    """A model's verdict on a free-form Chinese answer that the deterministic
    rules (services/sentence_check.py) could neither accept nor reject --
    e.g. 我很开心。 for an expected 我很高兴。. Returns {category, feedback}
    with category in JUDGE_CATEGORIES, or None when no model answers (the
    caller then keeps the rules' own verdict; nothing is guessed)."""
    if _active_provider() != "gemini" or not answer:
        return None
    system = (
        "You grade one Chinese sentence written by a language learner. "
        f"{_GRAMMAR_FACTS} "
        "Judge whether the learner's sentence does the task correctly. A different wording that is "
        "grammatical, natural and means the same is an acceptable ALTERNATIVE, not an error. "
        "Reply as JSON: {\"category\": one of " + ", ".join(f'"{c}"' for c in JUDGE_CATEGORIES)
        + ", \"feedback\": one or two short, kind sentences for the learner}. Categories: correct = "
        "same as the expected answer; alternative = different but correct; unnatural = grammatical but "
        "not how people say it; typo = one wrong character, the intent is clear; grammar = a grammar "
        "error; vocabulary = a wrong word; different = does not do the task. "
        + _language_rule(locale)
    )
    user = f"Task: {task}\nExpected answer: {expected}\n"
    if wrong:
        user += f"Sentence the learner had to correct: {wrong}\n"
    user += f"Learner's sentence: {answer}"
    try:
        data = json.loads(_gemini_chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=250, temperature=0.1, json_mode=True,
        ))
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("category") not in JUDGE_CATEGORIES:
        return None
    return {"category": data["category"], "feedback": _clean_feedback(data.get("feedback"), locale)}


ASSISTANT_NO_VISION = {
    "en": "I can't look at images or files right now — that needs the AI, which is unavailable. Type the text you want explained and I'll help as far as I can.",
    "ru": "Сейчас я не могу посмотреть изображение или файл — для этого нужен ИИ, а он недоступен. Напиши текст, который нужно объяснить, и я помогу, чем смогу.",
    "tg": "Ҳоло ман тасвир ё файлро дида наметавонам — барои ин зеҳни сунъӣ лозим аст, ки дастнорас аст. Матнеро, ки шарҳ додан лозим аст, нависед, ман то ҳадди имкон кӯмак мекунам.",
    "zh": "现在我看不了图片或文件——这需要 AI，而 AI 暂时无法使用。把要解释的文字打出来，我尽量帮你。",
}


def _assistant_system(context: dict, locale: str) -> str:
    return ASSISTANT_SYSTEM_TEMPLATE.format(
        learner=_learner_block(context),
        language=ASSISTANT_LANGUAGE_NAMES.get(locale, "English"),
        language_detail=ASSISTANT_LANGUAGE_DETAIL.get(locale, ""),
        compass=ASSISTANT_COMPASS_NAME.get(locale, ASSISTANT_COMPASS_NAME["en"]),
    )


def assistant_stream(messages: List[dict], context: dict, locale: str = "en"):
    """The assistant's reply as a stream of events (a generator of dicts):
    {"type": "meta", "source": "ai"|"offline"}, then {"type": "delta",
    "text"} chunks, then {"type": "done"} -- or {"type": "error"} if the
    model fails after it already started (the text so far stays with the
    learner). Before the first chunk every failure degrades to the offline
    helper, exactly like assistant_reply."""
    has_files = any(m.get("attachments") for m in messages)
    if _active_provider() == "gemini" and messages:
        stream = _gemini_stream([{"role": "system", "content": _assistant_system(context, locale)}] + messages,
                                max_tokens=1500, temperature=0.6)
        started = False
        try:
            for chunk in stream:
                if not started:
                    started = True
                    yield {"type": "meta", "source": "ai"}
                yield {"type": "delta", "text": _tg_clean_mixed_script(chunk) if locale == "tg" else chunk}
            yield {"type": "done"}
            return
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            if started:
                logger.warning("Assistant stream broke off: %s", type(exc).__name__)
                yield {"type": "error", "detail": "The answer was interrupted — you can ask again."}
                return
        finally:
            stream.close()
    yield {"type": "meta", "source": "offline"}
    if has_files:
        yield {"type": "delta", "text": ASSISTANT_NO_VISION.get(locale, ASSISTANT_NO_VISION["en"])}
    else:
        yield {"type": "delta", "text": _offline_assistant_reply(messages, context, locale)}
    yield {"type": "done"}


def evaluate_pet_teacher_explanation(
    mistake_summary: str,
    explanation: str,
    keywords: List[str],
    *,
    wrong_sentence: str = "",
    correct_sentence: str = "",
    correction: str = "",
    correction_ok: bool = True,
    locale: str = "en",
) -> dict:
    """Judge whether the learner's explanation of a grammar rule shows real
    understanding, not just a lucky correction.

    The model now sees the whole case -- the companion's wrong sentence, the
    right one, the learner's own correction and whether the rules already
    accepted it -- and answers in the learner's language. Before, it got
    only the rule, wrote its feedback in Chinese whatever the UI language,
    and could lecture a learner about a correction that was right.

    Offline mode checks whether the explanation touches one of the rule's
    keywords; an "explanation" that is only the sentence again is not one."""
    from app.services.sentence_check import normalize

    restated = bool(explanation) and normalize(explanation) in {
        normalize(correction), normalize(correct_sentence)}
    if restated:
        return {"understood": False, "feedback": "", "restated": True}
    if _active_provider() == "gemini" and explanation:
        system = (
            "You are a kind Chinese grammar teacher. A learner corrected a sentence and now explains, in "
            "their own words and in any language, WHY the correction is right. Decide whether the "
            "explanation shows they understand the rule. Do not demand perfect wording or terminology: a "
            "short explanation that states the rule is enough. "
            f"{_GRAMMAR_FACTS} "
            + ("The learner's correction is RIGHT; never say or imply that it is wrong. "
               if correction_ok else "")
            + 'Reply as JSON: {"understood": true or false, "feedback": one or two short sentences: '
            "if understood, confirm what they got right; if not, say what the explanation is missing "
            "and give a hint toward the rule -- without simply giving the whole answer away}. "
            + _language_rule(locale)
        )
        user = (
            f"Wrong sentence: {wrong_sentence}\nCorrect sentence: {correct_sentence}\n"
            f"Learner's correction: {correction}\nThe rule: {mistake_summary}\n"
            f"Words a good explanation often uses: {', '.join(keywords)}\n"
            f"Learner's explanation: {explanation}"
        )
        try:
            data = json.loads(_gemini_chat(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                max_tokens=300, temperature=0.2, json_mode=True,
            ))
            if isinstance(data, dict) and isinstance(data.get("understood"), bool):
                return {
                    "understood": data["understood"],
                    "feedback": _clean_feedback(data.get("feedback"), locale),
                    "restated": False,
                }
        except (KeyError, IndexError, TypeError, ValueError, httpx.HTTPError):
            pass
    understood = _contain(explanation, *keywords)
    return {"understood": understood, "feedback": "", "restated": False}