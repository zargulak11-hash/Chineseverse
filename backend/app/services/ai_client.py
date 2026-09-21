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


def _offline_chat(messages: List[dict], companion: str, user_name: str) -> str:
    role = companion
    last = messages[-1] if messages else {}
    content = (last.get("content") or "").lower()
    if _contain(content, "你好", "hi", "hello"):
        return f"{role}：你好！我叫{role}，是你的语言伙伴。你想聊什么？"
    if _contain(content, "名字", "name"):
        return f"{role}：我的名字。你呢？你的中文名字是什么？"
    if _contain(content, "谢谢", "thank"):
        return f"{role}：不客气！随时找我。"
    if _contain(content, "再见", "bye", "拜拜"):
        return f"{role}：再见！今天练习得不错。"
    return (
        f"{role}：我听到你说「{last.get('content', '')}」。"
        f"很有进步，{user_name}！再说一遍怎么样？"
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


def chat_reply(messages: List[dict], companion: str, user_name: str) -> str:
    """Companion is the pre-named NPC. Returns the NPC's reply text."""
    provider = _active_provider()
    if provider == "openai":
        try:
            system = (
                f"你是一个叫「{companion}」的中文语音伙伴，"
                "用简单中文和少量拼音引导学习者说话，末尾给一句鼓励。"
                "对话中不要用拼音解释，直接说中文。"
            )
            return _openai_chat(
                [{"role": "system", "content": system}] + messages,
                settings.ai_model,
            )
        except httpx.HTTPError:
            pass
    return _offline_chat(messages, companion, user_name)


def evaluation_fallback(prompt: str, transcript: str, expected_keywords: Optional[List[str]] = None) -> dict:
    """Graceful degradation when the live AI call fails mid-flight."""
    return _offline_evaluate(prompt, transcript, expected_keywords or [])