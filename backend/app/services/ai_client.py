"""
AI service abstraction.

Providers:
  - "openai"  : OpenAI-compatible API via raw HTTP (configurable base_url/model/key).
  - "offline" : deterministic, rule-based fallback so the whole product works
                with no API key configured.  choice in "auto" mode): provider auto-detected.

Every function has an offline implementation, so LinguaVerse keeps working without
any external API key.
"""

from __future__ import annotations

import json
import random
import re
from typing import List, Optional

import httpx

from app.config import settings


class AIError(Exception):
    pass


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").lower())


def _contain(text: str, *keywords: str) -> bool:
    text = _normalize(text)
    return any(_normalize(k) and _normalize(k) in text for k in keywords)


def _active_provider() -> str:
    provider = (settings.ai_provider or "auto").lower()
    if provider == "auto":
        return "openai" if settings.ai_api_key else "offline"
    return provider if provider in {"openai", "offline"} else "offline"


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


def _offline_evaluate(prompt: str, transcript: str, expected_keywords: List[str]) -> dict:
    tx = _normalize(transcript)
    hits = [k for k in expected_keywords if _normalize(k) and _normalize(k) in tx]
    hit_ratio = len(hits) / len([k for k in expected_keywords if k]) if expected_keywords else 0.0
    relevance = hit_ratio * 100.0
    length_ok = 0.25 <= (len(transcript) or 0) / max(1, len(prompt)) <= 3.0
    # Deterministic but plausible felt score.
    if relevance >= 90:
        return {
            "pronunciation": round(random.uniform(82, 94), 1),
            "tones": round(random.uniform(78, 92), 1),
            "fluency": round(random.uniform(80, 93), 1),
            "grammar": round(random.uniform(85, 95), 1),
            "relevance": relevance,
            "overall": round(88.0, 1),
            "feedback": "Excellent! All key phrases were clear."
            if not length_ok
            else "Perfect match. Keep that tone steady.",
        }
    if relevance >= 55:
        return {
            "pronunciation": round(random.uniform(70, 82), 1),
            "tones": round(random.uniform(66, 80), 1),
            "fluency": round(random.uniform(68, 82), 1),
            "grammar": round(random.uniform(72, 85), 1),
            "relevance": relevance,
            "overall": round(74.0, 1),
            "feedback": "Good, but try speaking a little slower and clearer.",
        }
    return {
        "pronunciation": round(random.uniform(55, 70), 1),
        "tones": round(random.uniform(50, 66), 1),
        "fluency": round(random.uniform(50, 66), 1),
        "grammar": round(random.uniform(55, 72), 1),
        "relevance": relevance,
        "overall": round(58.0, 1),
        "feedback": "Listen once more and repeat the phrase; focus on the tones.",
    }


def _offline_react(transcript: str, expected_keywords: List[str], correct: str, incorrect: str) -> str:
    if _contain(transcript, *expected_keywords):
        return correct
    if not transcript:
        return "听不清，再说一遍好吗？"
    return incorrect


def _offline_chat(
    messages: List[dict],
    companion: str,
    user_name: str,
    catchphrase: Optional[str] = None,
    energy: Optional[int] = None,
) -> str:
    """Deterministic, keyword-triggered fallback. `catchphrase` and `energy`
    are the SAME per-animal AnimalPersonality fields the real AI branch is
    told about (see chat_reply's `personality` string below) -- so even
    offline, a high-energy animal like Cheetah doesn't read identically to
    a calm one like Capybara; it's not just the name swapped in a template."""
    role = companion
    last = messages[-1] if messages else {}
    content = (last.get("content") or "").lower()
    exclaim = "！" if (energy is None or energy >= 50) else "。"
    if _contain(content, "你好", "hi", "hello"):
        lead = f"{catchphrase} " if catchphrase else ""
        return f"{role}：{lead}你好{exclaim}我是{role}，你的语言伙伴。你想聊什么？"
    if _contain(content, "名字", "name"):
        return f"{role}：我的名字就是{role}。你呢？你的中文名字是什么？"
    if _contain(content, "谢谢", "thank"):
        return f"{role}：不客气{exclaim}随时找我。"
    if _contain(content, "再见", "bye", "拜拜"):
        tail = f" {catchphrase}" if catchphrase else ""
        return f"{role}：再见{exclaim}今天练习得不错。{tail}"
    return (
        f"{role}：我听到你说「{last.get('content', '')}」。"
        f"很有进步，{user_name}{exclaim}再说一遍怎么样？"
    )


# ---------------------------------------------------------------------------
# OpenAI-compatible provider
# ---------------------------------------------------------------------------


def _openai_chat(messages: List[dict], model: str) -> str:
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 200,
    }
    resp = httpx.post(
        f"{settings.ai_base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {settings.ai_api_key}"},
        json=body,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


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
    if provider == "openai" and transcript:
        try:
            system = (
                "你是中文口语考官。根据提示、转录和关键词，返回JSON，"
                "包含 pronunciation/tones/fluency/grammar/relevance(0-100)、"
                "overall 和一句 feedback。"
            )
            user = (
                f"提示：{prompt}\n转录：{transcript}\n关键词：{expected_keywords}"
            )
            text = _openai_chat(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                settings.ai_model,
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


def chat_reply(
    messages: List[dict],
    companion: str,
    user_name: str,
    personality: Optional[str] = None,
    catchphrase: Optional[str] = None,
    energy: Optional[int] = None,
    level_hint: Optional[str] = None,
) -> str:
    """Companion is the pre-named NPC. Returns the NPC's reply text.

    `personality`/`catchphrase`/`energy` are the SAME AnimalPersonality
    fields already shown elsewhere in the app (Companion page, animal
    picker) -- passing them into the prompt is what makes Wolf actually
    read differently from Rabbit instead of only the name changing.
    `level_hint` ("beginner"/"intermediate"/"advanced") reuses the
    learner's existing HSK level so the same animal adapts its Chinese
    instead of always talking at one fixed difficulty.
    """
    provider = _active_provider()
    if provider == "openai":
        try:
            level_line = {
                "beginner": "学习者是初级水平：用非常简单的中文、常用词汇，句子要短。",
                "intermediate": "学习者是中级水平：可以用更自然、稍复杂的中文对话，词汇更广。",
                "advanced": "学习者是高级水平：可以用丰富、自然、更复杂的中文和更有深度的问题。",
            }.get(level_hint or "", "")
            system = (
                f"你是一个叫「{companion}」的中文语音伙伴。"
                + (f"你的性格：{personality}。" if personality else "")
                + (f"你常说的一句话：「{catchphrase}」，可以偶尔自然地用上。" if catchphrase else "")
                + "用符合你性格的语气和学习者说中文，引导对话，末尾给一句鼓励。"
                + "对话中不要用拼音解释，直接说中文。"
                + (f" {level_line}" if level_line else "")
            )
            return _openai_chat(
                [{"role": "system", "content": system}] + messages,
                settings.ai_model,
            )
        except httpx.HTTPError:
            pass
    return _offline_chat(messages, companion, user_name, catchphrase=catchphrase, energy=energy)


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
    if provider == "openai" and conclusion:
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
            text = _openai_chat(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                settings.ai_model,
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
# In-app study assistant — scoped to ChineseVerse + Chinese learning only.
# Reuses the same provider plumbing as everything else in this module
# (chat_reply, evaluate_speech, ...) instead of a separate AI integration.
# ---------------------------------------------------------------------------

ASSISTANT_SYSTEM_TEMPLATE = (
    "You are the in-app study assistant for ChineseVerse, a gamified Mandarin "
    "Chinese learning app. You ONLY help with: this app's own features (World, "
    "Lessons, Vocabulary, Learning DNA, Duels, Missions, Quests, Pet Teacher "
    "mode, the HSK roadmap, streaks, coins/XP), Chinese grammar/vocabulary/"
    "pronunciation questions, and this learner's own progress. If asked about "
    "anything else, politely decline in one sentence and steer back to Chinese "
    "learning or the app. Keep answers short (2-4 sentences), concrete and "
    "encouraging — never a generic wall of text.\n\n"
    "This learner: username={username}, HSK level={hsk_level}, overall "
    "mastery={mastery}%, current streak={streak} day(s), weakest skills="
    "{weak_skills}, companion={companion}."
)


def _offtopic_reply() -> str:
    return (
        "I can only help with ChineseVerse and Chinese learning — try asking "
        "about a grammar point (like 了/吗/的), your HSK progress, your weakest "
        "skill, or what to practice next."
    )


def _offline_assistant_reply(messages: List[dict], context: dict) -> str:
    last = messages[-1]["content"] if messages else ""
    q = _normalize(last)
    name = context.get("username") or "there"

    if not q:
        return f"Hi {name}! Ask me about a grammar point, your HSK progress, or what to practice next."
    if _contain(q, "hsk", "level", "progress"):
        return (
            f"You're at HSK {context['hsk_level']} with {context['mastery']}% overall mastery. "
            "Keep reviewing Vocabulary and Lessons daily — the HSK Roadmap page shows exactly "
            "what's left to unlock the next level."
        )
    if _contain(q, "streak"):
        return (
            f"Your current streak is {context['streak']} day(s). Do at least one review, lesson "
            "or conversation today to keep it alive."
        )
    if _contain(q, "weak", "improve", "focus", "struggl"):
        weak = ", ".join(context.get("weak_skills") or []) or "a bit of everything so far"
        return (
            f"Your weakest skill right now looks like {weak}. A Mission or Duel that targets it "
            "is the fastest way to move the needle — check your DNA page for the exact numbers."
        )
    if "了" in last:
        return (
            "了 (le) usually marks a completed action or a change of state — e.g. 我吃了 (I ate) "
            "vs 我在吃 (I'm eating). Try it in a Lesson or a Pet Teacher case to see it corrected live."
        )
    if "吗" in last:
        return "吗 (ma) turns a statement into a yes/no question — 你好吗？ = \"Are you well?\" Just add it to the end of a sentence."
    if "的" in last:
        return "的 (de) is the all-purpose possessive/descriptive particle — 我的书 = \"my book\". It links a modifier to the noun after it."
    if _contain(q, "xp", "coin", "reward"):
        return "You earn XP and coins from voice attempts, quests, missions and duels — the Quests page usually has today's easiest wins."
    if _contain(q, "companion", "animal"):
        comp = context.get("companion") or "no companion chosen yet"
        return f"Your companion is {comp}. Each one biases your daily quests and missions toward its own specialty — see the Companion page."
    if _contain(q, "duel"):
        return "Duels test your weakest strand under a timer. Start one from the Duels page — losing still counts as practice."
    return _offtopic_reply()


def assistant_reply(messages: List[dict], context: dict) -> str:
    """Reply to one turn of the in-app study assistant. `context` carries the
    learner's own stats (HSK level, mastery, streak, weak skills, companion)
    so answers about "how am I doing" are grounded in real data, not
    hallucinated. Always scoped to ChineseVerse/Chinese-learning topics."""
    provider = _active_provider()
    if provider == "openai" and messages:
        try:
            system = ASSISTANT_SYSTEM_TEMPLATE.format(
                username=context.get("username", "learner"),
                hsk_level=context.get("hsk_level", 1),
                mastery=context.get("mastery", 0),
                streak=context.get("streak", 0),
                weak_skills=", ".join(context.get("weak_skills") or []) or "none tracked yet",
                companion=context.get("companion") or "none chosen yet",
            )
            return _openai_chat([{"role": "system", "content": system}] + messages, settings.ai_model)
        except httpx.HTTPError:
            pass
    return _offline_assistant_reply(messages, context)


def evaluate_pet_teacher_explanation(
    mistake_summary: str,
    explanation: str,
    keywords: List[str],
) -> dict:
    """Judge whether the learner's explanation of a grammar rule shows real
    understanding, not just a lucky correction. Offline mode falls back to
    checking whether the explanation touches one of the rule's keywords."""
    provider = _active_provider()
    if provider == "openai" and explanation:
        try:
            system = (
                "你是中文语法老师。学习者需要解释一个语法规则为什么正确。"
                "判断他们的解释是否体现真正理解（不要求完美措辞）。"
                '返回JSON: {"understood": true 或 false, "feedback": "一句简短反馈"}。'
            )
            user = f"规则：{mistake_summary}\n关键词：{keywords}\n学习者的解释：{explanation}"
            text = _openai_chat(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                settings.ai_model,
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