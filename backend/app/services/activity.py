"""Real per-action activity tracking, extending UserStreak (which only ever
tracked day-level streak counters) with an actual event log — this is what
the Progress page's Learning Rhythm stats, time-by-section breakdown, and
activity heatmap are computed from.

`minutes` per action type is an estimated duration weight, not a measured
one — there is no active-focus session timer anywhere in this app — but it
is a fixed, honest weight assigned the same way for every event of that
type, not a per-request invented number.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app import models
from app.services.gamification import sync_streak

# action_type -> (section, estimated minutes)
ACTION_WEIGHTS: dict[str, tuple[str, float]] = {
    "voice_attempt": ("world", 0.6),
    "case_solve": ("world", 4.0),
    "vocab_review": ("vocabulary", 0.3),
    "lesson_complete": ("lessons", 8.0),
    "duel_finish": ("duels", 3.0),
    "quest_claim": ("quests", 0.5),
    "mission_complete": ("missions", 2.0),
    "pet_teacher_answer": ("pet_teacher", 1.5),
    "practice_answer": ("practice", 0.4),
    "hanzi_review": ("hanzi", 0.3),
    "hanzi_write": ("hanzi", 1.0),
    "grammar_practice": ("grammar", 0.5),
    "real_life_scene": ("real_life", 3.0),
    "sentence_lesson": ("sentence", 2.0),
    "detective_case": ("detective", 4.0),
    "sound_world": ("sound_world", 3.0),
    "internet_read": ("internet", 3.0),
    "tones_practice": ("foundation", 2.0),
    "skill_check": ("practice", 3.0),  # services/diagnostic.py
    "lesson_step": ("lessons", 2.0),  # a lesson's guided step (services/lesson_flow.py)
    "story_read": ("stories", 4.0),
    # Reading a book (services/stories.py): a chapter read to its end, the
    # whole book finished, listening to it, asking for help with a sentence.
    "story_chapter": ("stories", 3.0),
    "story_book": ("stories", 0.0),
    "story_listen": ("stories", 0.5),
    "story_explain": ("stories", 0.3),
    "word_saved": ("vocabulary", 0.2),
    # AI roleplay (services/roleplay.py): a message sent, a scenario finished.
    "roleplay_turn": ("roleplay", 1.0),
    "roleplay_finish": ("roleplay", 0.5),
    "sentence_saved": ("stories", 0.2),
    # Tone Coach (services/tone_coach.py): one word said and judged.
    "tone_attempt": ("foundation", 0.3),
}

SECTION_LABELS: dict[str, str] = {
    "world": "World & Conversations",
    "vocabulary": "Vocabulary",
    "lessons": "Lessons",
    "duels": "Duels",
    "quests": "Quests",
    "missions": "Missions",
    "pet_teacher": "Pet Teacher",
    "practice": "Practice & Review",
    "hanzi": "Hanzi",
    "grammar": "Grammar",
    "real_life": "Real Chinese",
    "sentence": "Sentence Lessons",
    "detective": "Detective Mode",
    "sound_world": "Sound World",
    "internet": "Chinese Internet",
    "foundation": "Sounds & tones",
    "stories": "Chinese Stories",
    "roleplay": "AI Roleplay",
}


def log_activity(db: Session, user: models.User, action_type: str, when: datetime | None = None) -> bool:
    """Record one real learning action. Returns True when it was the first
    of the learner's day (the day just started counting toward the streak)."""
    section, minutes = ACTION_WEIGHTS.get(action_type, ("other", 1.0))
    at = when or datetime.utcnow()
    db.add(
        models.ActivityEvent(
            user_id=user.id,
            section=section,
            action_type=action_type,
            minutes=minutes,
            created_at=at,
        )
    )
    # Every real learning action logs here, so this is also -- and the only
    # place -- where a day counts toward the streak. Before, only practice
    # answers and voice attempts touched the streak: days spent on Hanzi,
    # vocabulary, grammar, lessons, duels, cases, Pet Teacher or quests
    # filled the heatmap but never extended the streak. Opening the app,
    # pinging it or choosing a companion is not learning and never counts.
    return sync_streak(db, user, at)
