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
        {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
        for m in messages
        if m.get("role") in ("user", "assistant")
    ]
    config: dict = {"temperature": temperature, "maxOutputTokens": max_tokens}
    if "flash" in settings.gemini_model:
        # 2.5 Flash "thinks" by default and those hidden tokens are taken
        # out of maxOutputTokens, which left short replies empty. Flash
        # models accept a zero budget (Pro models don't, so only here).
        config["thinkingConfig"] = {"thinkingBudget": 0}
    if json_mode:
        # The graders json.loads() the reply; without this Gemini tends to
        # wrap it in a ```json fence.
        config["responseMimeType"] = "application/json"
    body: dict = {"contents": contents, "generationConfig": config}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    return body


def _gemini_chat(
    messages: List[dict],
    max_tokens: int = 200,
    temperature: float = 0.8,
    json_mode: bool = False,
) -> str:
    url = f"{settings.gemini_base_url.rstrip('/')}/models/{settings.gemini_model}:generateContent"
    try:
        resp = httpx.post(
            url,
            # Key in a header, not the ?key= query string, so it can't end up
            # in URL logs or exception messages.
            headers={"x-goog-api-key": settings.gemini_api_key or ""},
            json=_gemini_payload(messages, max_tokens, temperature, json_mode),
            timeout=30,
        )
        resp.raise_for_status()
        try:
            candidate = resp.json()["candidates"][0]
            parts = candidate.get("content", {}).get("parts") or []
            content = "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            # A blocked prompt comes back with no candidates at all. Every
            # caller already degrades to offline on ValueError.
            raise ValueError(f"Unexpected Gemini response shape: {type(exc).__name__}") from exc
    except httpx.HTTPStatusError as exc:
        # Log the status only -- never the request (it carries the key).
        logger.warning("Gemini returned HTTP %s", exc.response.status_code)
        raise
    except httpx.HTTPError as exc:
        logger.warning("Gemini unreachable: %s", type(exc).__name__)
        raise
    if not content.strip():
        # e.g. finishReason SAFETY / MAX_TOKENS with no text
        raise ValueError(f"Gemini returned no text (finishReason={candidate.get('finishReason')})")
    return content.strip()


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
    "You are the ChineseVerse assistant, built into ChineseVerse, a gamified "
    "app for learning Mandarin Chinese (HSK 1-9 roadmap, lessons, vocabulary, "
    "Hanzi, grammar, server-graded practice, spaced-repetition Review, "
    "Learning DNA skill profile, companions, Daily Voice Companion, Duels, "
    "Missions, Quests, Pet Teacher mode, streaks, XP and coins).\n\n"
    "How to behave:\n"
    "- Be a helpful, friendly, conversational assistant. Answer the question "
    "the learner actually asked.\n"
    "- You are especially strong at Chinese: grammar, vocabulary, Hanzi, "
    "pronunciation and tones, HSK preparation, study plans and Chinese "
    "culture. Give concrete examples with characters and pinyin when useful.\n"
    "- General questions (travel, science, everyday topics, small talk) are "
    "fine: answer them naturally. Do not refuse them, do not say you only "
    "help with ChineseVerse, and do not force every topic back to studying. "
    "A light, optional Chinese tie-in is welcome only when it fits.\n"
    "- Use the learner data below when it is relevant (their progress, what "
    "to practice next, how to prepare for HSK). It is the ONLY data you have "
    "about them: never invent scores, streaks, mastered words, completed "
    "lessons, Learning DNA numbers or achievements. If something is not "
    "listed, say you don't have that information.\n"
    "- You are read-only: you cannot change progress, XP, streaks, mastery or "
    "lessons, and must never claim you did. Progress only changes when the "
    "learner practises in the app.\n"
    "- Keep answers focused: usually a short paragraph or a few bullet points; "
    "go longer only when the learner asks for depth. Plain text, no tables.\n\n"
    "Learner data (from the ChineseVerse database):\n{learner}\n\n"
    "LANGUAGE: always reply in {language} -- the language this learner selected "
    "in the app -- even if they write to you in another language. Chinese "
    "examples (characters, pinyin) stay in Chinese; everything else is {language}."
)

# The app's selected UI language (X-Locale) decides the assistant's reply
# language, the same way it localizes every other screen. Names are written
# in English because they go into the English system prompt above.
ASSISTANT_LANGUAGE_NAMES = {"en": "English", "ru": "Russian", "tg": "Tajik", "zh": "Simplified Chinese"}


def _learner_block(context: dict) -> str:
    """Only facts the router actually read from the database go in; a
    missing value is omitted rather than defaulted, so the model can't
    present a placeholder as the learner's real data."""
    lines = []
    if context.get("username"):
        lines.append(f"- username: {context['username']}")
    if context.get("hsk_level") is not None:
        lines.append(f"- current HSK level: {context['hsk_level']}")
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
    if context.get("weak_skills"):
        lines.append("- weakest Learning DNA skills: " + ", ".join(context["weak_skills"]))
    if context.get("completed_lessons") is not None:
        lines.append(f"- lessons completed: {context['completed_lessons']}")
    lines.append(f"- main companion: {context.get('companion') or 'none chosen yet'}")
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
            "is the fastest way to move the needle — check your DNA page for the exact numbers."
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
        "duel": "Duels test your weakest strand under a timer. Start one from the Duels page — losing still counts as practice.",
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
            "самый быстрый способ его подтянуть. Точные цифры — на странице ДНК."
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
        "duel": "Дуэли проверяют твой самый слабый навык на время. Начни дуэль на странице дуэлей — даже проигрыш засчитывается как практика.",
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
            "роҳи зудтарини беҳтар кардани он аст — рақамҳои дақиқ дар саҳифаи ДНК."
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
        "duel": "Дуэлҳо заифтарин маҳорати шуморо бо вақт месанҷанд. Дуэлро аз саҳифаи дуэлҳо оғоз кунед — ҳатто бохт ҳамчун машқ ҳисоб мешавад.",
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
        "weak": "你目前最薄弱的技能是{weak}。针对它的任务或对战是提升最快的方法——具体数据请看学习 DNA 页面。",
        "no_weak": "目前各方面都还在起步",
        "le": "了 (le) 通常表示动作完成或状态变化——例如 我吃了（已经吃过）和 我在吃（正在吃）。可以在课程或 Pet Teacher 案例中试一试，马上看到纠正。",
        "ma": "吗 (ma) 能把陈述句变成是非疑问句——你好吗？ 只要把它放在句末就可以。",
        "de": "的 (de) 是最常用的结构助词，表示所属或修饰——我的书 就是“属于我的书”。它把修饰语和后面的名词连接起来。",
        "xp": "语音练习、任务、使命和对战都能获得经验值和金币——任务页面通常有今天最容易完成的奖励。",
        "companion": "你的伙伴是{companion}。每个伙伴都会让每日任务和使命偏向它的专长——请查看伙伴页面。",
        "no_companion": "还没有选择伙伴",
        "duel": "对战会在限时内考查你最薄弱的方面。从对战页面开始一局吧——输了也算练习。",
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
            system = ASSISTANT_SYSTEM_TEMPLATE.format(
                learner=_learner_block(context),
                language=ASSISTANT_LANGUAGE_NAMES.get(locale, "English"),
            )
            reply = _gemini_chat(
                [{"role": "system", "content": system}] + messages,
                max_tokens=700,
                temperature=0.7,
            )
            return reply, "ai"
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
            # Unreachable API, exhausted credits (429) or a malformed reply:
            # degrade to the offline helper, never a 500.
            pass
    return _offline_assistant_reply(messages, context, locale), "offline"


def evaluate_pet_teacher_explanation(
    mistake_summary: str,
    explanation: str,
    keywords: List[str],
) -> dict:
    """Judge whether the learner's explanation of a grammar rule shows real
    understanding, not just a lucky correction. Offline mode falls back to
    checking whether the explanation touches one of the rule's keywords."""
    provider = _active_provider()
    if provider == "gemini" and explanation:
        try:
            system = (
                "你是中文语法老师。学习者需要解释一个语法规则为什么正确。"
                "判断他们的解释是否体现真正理解（不要求完美措辞）。"
                '返回JSON: {"understood": true 或 false, "feedback": "一句简短反馈"}。'
            )
            user = f"规则：{mistake_summary}\n关键词：{keywords}\n学习者的解释：{explanation}"
            text = _gemini_chat(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                json_mode=True,
            )
            data = json.loads(text)
            return {
                "understood": bool(data.get("understood")),
                "feedback": str(data.get("feedback") or ""),
            }
        except (KeyError, ValueError, httpx.HTTPError):
            pass
    understood = _contain(explanation, *keywords)
    return {"understood": understood, "feedback": ""}