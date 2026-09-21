"""Learning DNA: a compact profile of the learner built from real activity."""

from __future__ import annotations

from typing import Dict

from app import models

ARCHETYPES = [
    ("Globetrotter", lambda d: (d.get("speaking", 0) + d.get("listening", 0)) / 2 >= 80),
    ("Poet", lambda d: (d.get("grammar", 0) + d.get("writing", 0)) / 2 >= 80),
    ("Polyglot Rookie", lambda d: d.get("vocabulary", 0) >= 70),
    ("Ninja Lisper", lambda d: d.get("tones", 0) >= 80),
    ("Night Owl", lambda d: d.get("reaction_speed", 0) >= 80),
    ("Scholar", lambda d: (d.get("reading", 0) + d.get("memory", 0)) / 2 >= 80),
    ("Explorer of Words", lambda d: True),
]

CODE_TO_KEY = {
    "speaking": "speaking",
    "listening": "listening",
    "reading": "reading",
    "writing": "writing",
    "vocabulary": "vocabulary",
    "grammar": "grammar",
    "tones": "tones",
    "memory": "memory",
    "reaction_speed": "reaction_speed",
}


def _util(user_skills) -> Dict[str, float]:
    out = {}
    for s in user_skills:
        if s.skill and s.skill.code in CODE_TO_KEY:
            out[s.skill.code] = s.mastery
    return out


def compute_dna(user: models.User) -> dict:
    skills = _util(user.user_skills)
    attempts = list(user.voice_attempts)
    active = [w for w in user.user_vocabulary if w.status == "mastered"]

    if not attempts and not active and not skills:
        overall = 0.0
    else:
        voice_boost = min(10.0, sum(a.tones or 0 for a in attempts) / max(1, len(attempts)) * 0.1)
        vocab_boost = min(15.0, len(active) * 1.0)
        base = sum(skills.values()) / max(1, len(skills)) if skills else 30.0
        overall = min(100.0, base * 0.85 + voice_boost + vocab_boost)

    weakest = min(skills, key=skills.get) if skills else None
    strongest = max(skills, key=skills.get) if skills else None
    arch = "Seedling"
    for name, pred in ARCHETYPES:
        if pred(skills):
            arch = name
            break

    strengths = [s.skill.name for s in user.user_skills if s.skill and s.mastery >= 70]
    weaknesses = [s.skill.name for s in user.user_skills if s.skill and s.mastery <= 30]

    recommendations = []
    if "tones" in skills and skills["tones"] < 50:
        recommendations.append("Run voice drills to sharpen your tones.")
    if not active:
        recommendations.append("Start mastering the HSK1 vocabulary deck.")

    return {
        "overall": round(overall, 1),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "archetype": arch,
        "skills": {CODE_TO_KEY[s.skill.code]: round(s.mastery, 1) for s in user.user_skills if s.skill and s.skill.code in CODE_TO_KEY},
        "weakest_skill": weakest if weakest else None,
        "strongest_skill": strongest if strongest else None,
        "weight": round(niche_factor(user), 2),
        "voice_attempts": len(attempts),
        "words_mastered": len(active),
        "recommendations": recommendations,
    }


def niche_factor(user: models.User) -> float:
    from datetime import datetime, timedelta

    recent = [a for a in user.voice_attempts if a.created_at and a.created_at > datetime.utcnow() - timedelta(days=7)]
    mastered = len([w for w in user.user_vocabulary if w.status == "mastered"])
    return min(1.0, len(recent) * 0.05 + mastered * 0.02)


WEIGHTS = (("speaking", 0.5), ("listening", 0.2), ("tones", 0.3))


def apply_voice_to_skills(user: models.User, attempt: models.VoiceAttempt) -> None:
    for code, weight in WEIGHTS:
        us = next((s for s in user.user_skills if s.skill and s.skill.code == code), None)
        if us is None:
            continue
        delta = min(100.0, (attempt.overall or 0.0) * weight)
        us.mastery = round(min(100.0, us.mastery + delta * 0.05), 1)
        us.xp += int(delta)
        us.last_updated = attempt.created_at