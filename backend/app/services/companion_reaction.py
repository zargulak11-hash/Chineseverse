"""The permanent companion's emotional reaction to REAL learning events.

Every reaction is derived from something the server just graded or stored --
the answers of a practice session (the session itself is the "what just
happened" memory), an item's own history (times missed, status before/after
the answer), a completed stroke-order quiz, or a Learning DNA skill that the
same request genuinely moved. Nothing here is random and nothing here writes
progress: these functions only *read* results and describe them.

A reaction is a plain dict (kept backward compatible with the old
{mood, event, streak} shape the frontend already consumed):

    mood       one of MOODS -- drives the animal's visual state
    event      what happened: answer, complete, lesson_complete, ...
    cause      why this mood (frontend i18n key + Chinese line below)
    zh         a short Chinese line the companion says (Chinese is never
               translated; the explanation around it is localized client-side)
    streak     trailing correct answers in this session
    miss_streak trailing wrong answers in this session
    accuracy   % correct of the answers graded so far (None before any)
    focus      the real curriculum item the reaction is about (or None)
    words      lesson start only: the lesson's real words, previewed
    skill      a real DNA skill this event moved ({code, value, ...}) or None
    milestone  "mastered", "new_item", "skill_up", "writing_mastered", ...
    companion  {"slug"} of the user's PERMANENT companion (user.animal_id) --
               never the Daily Voice Companion, which is session-only

Tone rule: moods are never shaming. "worried"/"sad" are the companion
feeling it *with* the learner; "frustrated" is playful and aimed at the
tricky word ("this word is naughty!"), never at the learner.
"""

from __future__ import annotations

import math

from app import models

MOODS = (
    "neutral", "happy", "excited", "proud", "encouraging",
    "worried", "sad", "frustrated", "serious", "celebrating",
)

# A DNA skill reaction fires only when a real bump crosses one of these
# boundaries -- every correct answer nudges a skill, and cheering each +2
# would be noise rather than a milestone.
SKILL_STEP = 10

# Question type -> the DNA skill the answer mainly trains (mirrors the
# bump_skill calls in services/practice.py::_record).
PRIMARY_SKILL = {
    "meaning_to_word": "vocabulary",
    "word_to_meaning": "vocabulary",
    "listen_to_word": "listening",
    "char_to_meaning": "reading",
    "char_to_pinyin": "tones",
    "example_to_point": "grammar",
}

_NOUN = {"vocab": "词", "hanzi": "字", "grammar": "语法"}

_ZH = {
    # answer, correct
    "correct": "很好！",
    "new_item": "又学会一个新{noun}！",
    "recovering": "对了！继续加油！",
    "streak": "太棒了！",
    "hot_streak": "你真厉害！",
    "comeback": "这次对了，真棒！",
    "mastered": "这个{noun}你已经掌握了！",
    "skill_up": "你进步了！",
    # answer, wrong
    "miss": "再试一次。",
    "streak_break": "没关系，继续加油！",
    "two_misses": "别着急，慢慢来。",
    "mistake_run": "别担心，我们一起复习。",
    "long_slump": "我陪着你，你可以做到！",
    "repeat_item": "这个{noun}我们再练习一次。",
    "tricky_item": "这个{noun}有点调皮！再看一遍。",
    # self-check ("I know it" / "still learning")
    "self_known": "很好！",
    "still_learning": "没关系，慢慢学。",
    # round / lesson / review completion
    "lesson_complete": "恭喜你！这一课完成了！",
    "outstanding": "太棒了！",
    "solid": "很好！继续加油！",
    "review_done": "复习完成，真棒！",
    "keep_practicing": "不错！还要多练习。",
    "needs_review": "别担心，我们一起复习。",
    "review_clear": "今天都复习完了！",
    # starts
    "lesson_start": "我们开始吧！",
    "review_start": "我们复习一下吧！",
    "session_start": "准备好了吗？",
    # handwriting
    "clean_trace": "写得真漂亮！",
    "good_trace": "写得很好！",
    "shaky_trace": "再写一次，会更好。",
    "writing_mastered": "这个字你会写了！",
}


def zh_line(cause: str, item_type: str | None = None) -> str:
    return _ZH.get(cause, "加油！").format(noun=_NOUN.get(item_type or "", "词"))


def companion_of(user: models.User) -> dict | None:
    """Always the permanent companion (user.animal_id)."""
    animal = user.animal
    return {"slug": animal.slug} if animal is not None else None


def skill_value(user: models.User, code: str) -> float | None:
    us = next((s for s in user.user_skills if s.skill and s.skill.code == code), None)
    return us.mastery if us is not None else None


def skill_crossing(code: str, before: float | None, after: float | None) -> dict | None:
    """A real DNA change worth reacting to: the skill rose across a
    SKILL_STEP boundary within this one request."""
    if before is None or after is None or after <= before:
        return None
    if math.floor(after / SKILL_STEP) <= math.floor(before / SKILL_STEP):
        return None
    return {"code": code, "value": round(after, 1), "delta": round(after - before, 1)}


def _run(answers: list) -> tuple[int, int, int, int | None]:
    """(streak, miss_streak, prior_miss_run, accuracy%) of a session so far.
    prior_miss_run is the run of misses just before the current correct
    streak -- how deep the hole was that the learner is climbing out of."""
    graded = [a for a in answers if a is not None]
    streak = miss_streak = 0
    for a in reversed(graded):
        if not a["correct"]:
            break
        streak += 1
    for a in reversed(graded):
        if a["correct"]:
            break
        miss_streak += 1
    prior_miss_run = 0
    for a in reversed(graded[: len(graded) - streak]):
        if a["correct"]:
            break
        prior_miss_run += 1
    accuracy = round(100 * sum(1 for a in graded if a["correct"]) / len(graded)) if graded else None
    return streak, miss_streak, prior_miss_run, accuracy


def _base(user: models.User, mood: str, event: str, cause: str, item_type: str | None = None, **extra) -> dict:
    out = {
        "mood": mood,
        "event": event,
        "cause": cause,
        "zh": zh_line(cause, item_type),
        "streak": 0,
        "miss_streak": 0,
        "accuracy": None,
        "focus": None,
        "skill": None,
        "milestone": None,
        "companion": companion_of(user),
    }
    out.update(extra)
    return out


# --------------------------------------------------------------------------- practice answers

def answer_reaction(
    user: models.User,
    answers: list,
    *,
    item_type: str,
    focus: dict | None,
    status_before: str | None,
    status_after: str,
    times_missed: int,
    skill: dict | None,
) -> dict:
    """Reaction to one graded practice answer. `answers` is the session's
    stored answer list INCLUDING this one; `times_missed` is the item's
    lifetime miss count after this answer; `status_before` is None when the
    learner met this item for the first time."""
    graded = [a for a in answers if a is not None]
    correct = bool(graded and graded[-1]["correct"])
    streak, miss_streak, prior_miss_run, accuracy = _run(answers)
    milestone = None
    if correct:
        if status_after == "mastered" and status_before != "mastered":
            mood, cause, milestone = "proud", "mastered", "mastered"
        elif skill is not None:
            mood, cause, milestone = "proud", "skill_up", "skill_up"
        elif streak >= 5:
            mood, cause = "excited", "hot_streak"
        elif times_missed > 0 and status_before is not None and streak == 1 and prior_miss_run == 0:
            # Got right an item that has tripped the learner up before.
            mood, cause = "proud", "comeback"
        elif streak >= 3:
            mood, cause = "proud", "streak"
        elif prior_miss_run >= 2 and streak == 1:
            mood, cause = "encouraging", "recovering"
        elif status_before is None:
            mood, cause, milestone = "happy", "new_item", "new_item"
        else:
            mood, cause = "happy", "correct"
    else:
        recent_misses = sum(1 for a in graded[-4:] if not a["correct"])
        streak_before = _streak_before_miss(graded)
        if miss_streak >= 4:
            mood, cause = "sad", "long_slump"
        elif miss_streak == 3 or recent_misses >= 3:
            mood, cause = "worried", "mistake_run"
        elif times_missed >= 3:
            mood, cause = "frustrated", "tricky_item"
        elif times_missed == 2:
            mood, cause = "serious", "repeat_item"
        elif miss_streak == 2:
            mood, cause = "worried", "two_misses"
        elif streak_before >= 3:
            mood, cause = "encouraging", "streak_break"
        else:
            mood, cause = "encouraging", "miss"
    return _base(
        user, mood, "answer", cause, item_type,
        streak=streak, miss_streak=miss_streak, accuracy=accuracy,
        focus=focus, skill=skill if cause == "skill_up" else None, milestone=milestone,
    )


def _streak_before_miss(graded: list) -> int:
    """Correct answers in a row right before the current (wrong) answer."""
    n = 0
    for a in reversed(graded[:-1]):
        if not a["correct"]:
            break
        n += 1
    return n


# --------------------------------------------------------------------------- starts / completion

def start_reaction(user: models.User, source: str, *, words: list[dict] | None = None, due: int = 0) -> dict:
    if source == "lesson":
        return _base(user, "happy", "lesson_start", "lesson_start", "vocab", words=words or [])
    if source == "review":
        return _base(user, "serious", "review_start", "review_start", due=due)
    return _base(user, "neutral", "session_start", "session_start")


def review_clear_reaction(user: models.User) -> dict:
    return _base(user, "happy", "review_clear", "review_clear")


def session_reaction(
    user: models.User,
    answers: list,
    total: int,
    *,
    source: str,
    lesson_completed: bool,
    focus: dict | None,
    skill: dict | None,
) -> dict:
    """Reaction to a finished round, from its real score:
    >= 90% celebrate, 70-89% happy, 50-69% neutral with a targeted item to
    revisit, < 50% worried-but-supportive with a pointer to Review."""
    graded = [a for a in answers if a is not None]
    score = sum(1 for a in graded if a["correct"]) / (total or 1)
    streak, miss_streak, _p, accuracy = _run(answers)
    if lesson_completed:
        event, mood, cause = "lesson_complete", "celebrating", "lesson_complete"
    else:
        event = "review_complete" if source == "review" else "complete"
        if score >= 0.9:
            mood, cause = "celebrating", "outstanding"
        elif score >= 0.7:
            mood, cause = ("proud", "review_done") if source == "review" else ("happy", "solid")
        elif score >= 0.5:
            mood, cause = "neutral", "keep_practicing"
        else:
            mood, cause = "worried", "needs_review"
    return _base(
        user, mood, event, cause, (focus or {}).get("item_type"),
        streak=streak, miss_streak=miss_streak, accuracy=accuracy,
        score=round(score * 100, 1), focus=focus, skill=skill,
        milestone="lesson_complete" if lesson_completed else None,
    )


def trained_skill(user: models.User, questions: list, answers: list) -> dict | None:
    """The DNA skill this round trained most (by correct answers), with its
    CURRENT real value -- a description of what already happened, not a
    new bump."""
    counts: dict[str, int] = {}
    for q, a in zip(questions, answers):
        if a is not None and a["correct"]:
            code = PRIMARY_SKILL.get(q["type"])
            if code:
                counts[code] = counts.get(code, 0) + 1
    if not counts:
        return None
    code = max(counts, key=lambda c: (counts[c], c))
    value = skill_value(user, code)
    if value is None:
        return None
    return {"code": code, "value": round(value, 1), "trained": counts[code]}


# --------------------------------------------------------------------------- single-item events

def write_reaction(
    user: models.User, *, total_mistakes: int, status_before: str | None, status_after: str,
    focus: dict, skill: dict | None,
) -> dict:
    """Reaction to a completed HanziWriter stroke-order quiz."""
    milestone = None
    if status_after == "mastered" and status_before != "mastered":
        mood, cause, milestone = "celebrating", "writing_mastered", "writing_mastered"
    elif skill is not None:
        mood, cause, milestone = "proud", "skill_up", "skill_up"
    elif total_mistakes == 0:
        mood, cause = "proud", "clean_trace"
    elif total_mistakes <= 2:
        mood, cause = "happy", "good_trace"
    else:
        mood, cause = "encouraging", "shaky_trace"
    return _base(
        user, mood, "hanzi_write", cause, "hanzi",
        focus=focus, skill=skill if cause == "skill_up" else None, milestone=milestone,
        mistakes=total_mistakes,
    )


def self_check_reaction(
    user: models.User, *, item_type: str, correct: bool, status_before: str | None, status_after: str,
    times_missed: int, focus: dict, skill: dict | None,
) -> dict:
    """Reaction to a "got it" / "still learning" self-check on one item."""
    milestone = None
    if correct:
        if status_after == "mastered" and status_before != "mastered":
            mood, cause, milestone = "proud", "mastered", "mastered"
        elif skill is not None:
            mood, cause, milestone = "proud", "skill_up", "skill_up"
        else:
            mood, cause = "happy", "self_known"
    elif times_missed >= 2:
        mood, cause = "serious", "repeat_item"
    else:
        mood, cause = "encouraging", "still_learning"
    return _base(
        user, mood, "self_check", cause, item_type,
        focus=focus, skill=skill if cause == "skill_up" else None, milestone=milestone,
    )
