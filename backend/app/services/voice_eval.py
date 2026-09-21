"""Voice evaluation pipeline. Assembles prompt + transcript + keywords into the
tone/relevance scores that feed the Learning DNA and the companion reaction."""

from __future__ import annotations

from typing import List, Optional

from app import models
from app.services import ai_client


def grade_turn(
    dialogue: Optional[models.Dialogue],
    transcript: str,
    expected_keywords: Optional[List[str]] = None,
) -> dict:
    """Grade one dialogue turn.

    Returns dict with score fields (same keys as VoiceAttempt columns) plus the
    companion reaction string derived from the correctness of the keywords.
    """
    prompt = dialogue.prompt if dialogue else ""
    keywords = expected_keywords or (dialogue.expected_keywords if dialogue else []) or []
    try:
        scores = ai_client.evaluate_speech(prompt, transcript, keywords)
    except ai_client.AIError:
        scores = ai_client.evaluation_fallback(prompt, transcript, keywords)

    reaction = None
    if dialogue and dialogue.reaction_correct:
        reaction = ai_client._offline_react(
            transcript, keywords,
            dialogue.reaction_correct or "很好！",
            dialogue.reaction_incorrect or "再说一遍好吗？",
        )

    return {
        "prompt_text": prompt,
        "spoken_text": transcript,
        "transcript": transcript,
        "pronunciation": scores["pronunciation"],
        "tones": scores["tones"],
        "fluency": scores["fluency"],
        "grammar": scores["grammar"],
        "relevance": scores["relevance"],
        "response_time_ms": 0,
        "overall": scores["overall"],
        "feedback": scores["feedback"],
        "reaction": reaction,
        "is_correct": scores["relevance"] >= 55,
    }