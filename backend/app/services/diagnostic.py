"""The skill check: what a learner already knows at a level, skill by skill,
and what needs practice.

The placement test (routers/onboarding.py) runs once, at sign-up, asks only
word meanings and sets every Learning Compass skill to the same value -- it
cannot say that someone reads HSK 3 words but cannot hear them, or knows the
characters but not their tones. A learner around HSK 3 who comes back had no
way to find out where they stand.

The skill check is a short graded round (practice source "diagnostic") at
the learner's level -- or a level they choose -- with PER_SKILL questions
for each skill, every one tagged with the skill it measures:

  vocabulary  see a word, choose its meaning
  listening   hear a word, choose its meaning
  reading     see a character, choose its meaning
  tones       hear a character, choose its pinyin among the same syllable
              in other tones
  grammar     read an example sentence, choose the grammar point it uses
  memory      see a meaning, type the word from memory (pinyin or hanzi)

It is graded by the server like any round (mastery, mistakes, Learning DNA,
XP all move for real), and its result is read back from the stored answers
-- nothing is stored twice. A skill answered right less than WEAK_BELOW of
the time is weak; journey.py makes the weakest one the next step until the
learner has practised it (a completed round of that skill's source after
the check). Nothing is estimated and nothing is random in the scoring.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app import models

PER_SKILL = 2
WEAK_BELOW = 0.5      # share of a skill's questions answered right
FRESH = timedelta(days=21)  # an older check no longer steers the next step

# skill -> (item type, question type)
SECTIONS = (
    ("vocabulary", "vocab", "word_to_meaning"),
    ("listening", "vocab", "listen_to_word"),
    ("reading", "hanzi", "char_to_meaning"),
    ("tones", "hanzi", "char_to_pinyin"),
    ("grammar", "grammar", "example_to_point"),
    ("memory", "vocab", "type_word"),
)
SKILLS = tuple(s for s, _, _ in SECTIONS)

# Where each skill is practised, and the practice source(s) whose completed
# round counts as having practised it after the check.
PRACTICE = {
    "vocabulary": ("/practice?source=vocab&level={level}", ("vocab", "review", "lesson")),
    "listening": ("/sound-world", ("sound", "pronunciation")),
    "reading": ("/practice?source=hanzi&level={level}", ("hanzi",)),
    "tones": ("/practice?source=pronunciation&env=tone_pairs", ("pronunciation", "tones")),
    "grammar": ("/practice?source=grammar&level={level}", ("grammar",)),
    # Review: the words the check found missing come back there, typed from
    # memory once known (source "recall" only holds words already known).
    "memory": ("/review", ("review", "recall")),
}


def _with_meaning(db: Session, ids: list[int], locale: str) -> set[int]:
    """Words whose meaning exists in the learner's language: a typed-recall
    prompt is the meaning, so an English gloss on a Tajik screen is no prompt
    (the same rule as practice._recall_ready)."""
    if locale == "en" or not ids:
        return set(ids)
    return {
        int(k) for (k,) in db.query(models.ContentTranslation.content_key).filter(
            models.ContentTranslation.content_type == "vocab_word",
            models.ContentTranslation.field == "meanings",
            models.ContentTranslation.locale == locale,
            models.ContentTranslation.content_key.in_([str(i) for i in ids]),
        )
    }


def build_questions(db: Session, user: models.User, level: int, rng: random.Random, locale: str,
                    translated: dict | None) -> list[dict]:
    from app.services import practice

    rows = {t: [r for r in practice._level_rows(db, t, level) if practice._usable(t, r)]
            for t in ("vocab", "hanzi", "grammar")}
    for pool in rows.values():
        rng.shuffle(pool)
    used: set[tuple[str, int]] = set()
    questions: list[dict] = []
    for skill, item_type, qtype in SECTIONS:
        pool = rows[item_type]
        if qtype == "type_word":
            ok = _with_meaning(db, [r.id for r in pool], locale)
            pool = [r for r in pool if r.id in ok]
        got = 0
        for row in pool:
            if got == PER_SKILL:
                break
            if (item_type, row.id) in used:
                continue
            if qtype == "type_word":
                q = {"type": qtype, "item_type": item_type, "item_id": row.id, "option_ids": []}
            else:
                q = practice._question(db, item_type, row, len(questions), rng, translated, qtype=qtype)
            if not q:
                continue
            if qtype == "char_to_pinyin":
                q["speak"] = True  # tones are heard (practice.render_session plays it)
            q["skill"] = skill
            used.add((item_type, row.id))
            questions.append(q)
            got += 1
    if questions:
        questions[0]["ctx"] = {"kind": "diagnostic", "level": level}
    return questions


def breakdown(session: models.PracticeSession) -> list[dict]:
    """Right answers per skill, from the round's own stored answers."""
    out = {s: {"skill": s, "correct": 0, "total": 0, "answered": 0} for s in SKILLS}
    for q, a in zip(session.questions or [], session.answers or []):
        s = q.get("skill")
        if s not in out:
            continue
        out[s]["total"] += 1
        if a is not None:
            out[s]["answered"] += 1
            out[s]["correct"] += 1 if a.get("correct") else 0
    level = ((session.questions or [{}])[0].get("ctx") or {}).get("level") or session.hsk_level or 1
    rows = []
    for s in SKILLS:
        r = out[s]
        if not r["total"]:
            continue
        r["share"] = round(r["correct"] / r["total"], 2)
        r["weak"] = r["share"] < WEAK_BELOW
        r["to"] = PRACTICE[s][0].format(level=level)
        rows.append(r)
    return rows


def latest(db: Session, user: models.User) -> dict | None:
    """The learner's most recent finished skill check: when, at which
    level, every skill's result, and the weak skills not yet practised
    since (each with where to practise it), weakest first."""
    s = (db.query(models.PracticeSession)
         .filter(models.PracticeSession.user_id == user.id, models.PracticeSession.source == "diagnostic",
                 models.PracticeSession.completed_at.isnot(None))
         .order_by(models.PracticeSession.completed_at.desc()).first())
    if s is None:
        return None
    skills = breakdown(s)
    since = {src for (src,) in db.query(models.PracticeSession.source).filter(
        models.PracticeSession.user_id == user.id, models.PracticeSession.completed_at > s.completed_at)}
    weak = sorted((r for r in skills if r["weak"] and not since.intersection(PRACTICE[r["skill"]][1])),
                  key=lambda r: (r["share"], SKILLS.index(r["skill"])))
    return {"session_id": s.id, "level": s.hsk_level, "at": s.completed_at.isoformat() + "Z",
            "fresh": datetime.utcnow() - s.completed_at <= FRESH, "score": s.score,
            "skills": skills, "weak": weak}
