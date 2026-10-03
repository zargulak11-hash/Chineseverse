"""The learner's journey: where they are, what to do now, what comes next.

ChineseVerse has many places to learn in; a beginner needs ONE next step.
This module reads the learner's own records -- completed practice rounds by
source, voice turns, completed lessons, the lesson path, the review queue,
read stories -- and answers three questions without inventing anything:

  foundation  the first steps of Chinese, in order. Each is done only when
              the learner really did it (a passed round, a real voice turn,
              a completed lesson...). Nothing is ever marked done for them.
  next        the one action recommended now: the first foundation step not
              done (while they are at HSK 1), then -- once the foundation is
              behind them or their level is past it -- due reviews when many
              are waiting, the current lesson on the HSK path, its exam when
              the level's lessons are all done, or a story at their level.
  roadmap     HSK 1-9 as stages a beginner understands (Foundation,
              Beginner, Growing, Intermediate, Advanced), each with its real
              lessons, words and stories, and the exam that opens the next.

A learner placed above HSK 1 (placement test, or progress made before) isn't
sent back through the foundation: its steps show "past it" (not "done").
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app import models

PASS = 60.0  # a foundation round counts at this score (percent)
REVIEW_FIRST_AT = 8  # due reviews that take priority over new material

# key -> (practice source or special evidence, route). Order = the path.
FOUNDATION = (
    ("tones", "/foundation"),
    ("characters", "/practice?source=hanzi&level=1"),
    ("first_lesson", "/lessons"),
    ("sentence", "/sentence"),
    ("listen", "/sound-world"),
    ("speak", "/real-chinese/talk/greet-grandma"),
    ("story", "/stories"),
    ("review", "/review"),
)

STAGES = ((1, "beginner"), (2, "beginner"), (3, "growing"), (4, "intermediate"), (5, "intermediate"),
          (6, "advanced"), (7, "advanced"), (8, "advanced"), (9, "advanced"))
STAGE_OF = dict(STAGES)

# Special places, and when each is worth suggesting (never hidden: these
# only decide what the journey puts forward).
FEATURES = (
    ("sound-world", "/sound-world", "start"),
    ("sentence", "/sentence", "first_lesson"),
    ("detective", "/detective", "first_lesson"),
    ("passport", "/passport", "any_activity"),
    ("dna", "/dna", "any_activity"),
    ("ecosystem", "/ecosystem", "words_20"),
    ("internet", "/internet", "level_2"),
    ("stories", "/stories", "start"),
    ("real-chinese", "/real-chinese", "start"),
)


def _sessions(db: Session, user: models.User) -> list[models.PracticeSession]:
    return (db.query(models.PracticeSession)
            .filter(models.PracticeSession.user_id == user.id, models.PracticeSession.completed_at.isnot(None))
            .all())


def evidence(db: Session, user: models.User) -> dict:
    """The real records each step is judged on."""
    done = _sessions(db, user)
    best: dict[str, float] = {}
    for s in done:
        best[s.source] = max(best.get(s.source, 0.0), s.score or 0.0)
    voice = db.query(models.VoiceAttempt.id).filter(models.VoiceAttempt.user_id == user.id).first() is not None
    lessons = db.query(models.Progress).filter_by(user_id=user.id, status="completed").count()
    known = (db.query(models.UserVocabulary.id)
             .filter(models.UserVocabulary.user_id == user.id,
                     models.UserVocabulary.status.in_(("reviewing", "mastered"))).count())
    from app.services import stories

    books = len(stories.read_slugs(db, user))
    return {"best": best, "voice": voice, "lessons": lessons, "known_words": known, "any": bool(done) or voice,
            "books": books}


def _step_done(key: str, ev: dict) -> bool:
    best = ev["best"]
    if key == "tones":
        return best.get("tones", 0.0) >= PASS
    if key == "characters":
        return best.get("hanzi", 0.0) >= PASS
    if key == "first_lesson":
        return ev["lessons"] >= 1
    if key == "sentence":
        return "sentence" in best
    if key == "listen":
        return "sound" in best
    if key == "speak":
        return ev["voice"]
    if key == "story":
        # A story round, or a book read to its end.
        return "story" in best or ev["books"] > 0
    if key == "review":
        return "review" in best
    return False


def journey(db: Session, user: models.User) -> dict:
    from app.services import lesson_path, practice
    from app.services.gamification import ensure_user_skills, user_rank

    ensure_user_skills(db, user)
    level, _ = user_rank(db, user)
    ev = evidence(db, user)
    state = lesson_path.path_state(db, user)

    # The foundation matters while the learner is at HSK 1. Above it (placed
    # by the test, or far along already) its steps are "past", not "done".
    past = level >= 2
    steps, current = [], None
    for key, to in FOUNDATION:
        done = _step_done(key, ev)
        if key == "first_lesson" and state.current is not None and state.current.level == 1:
            to = f"/lessons/{state.current.lesson.id}"
        status = "done" if done else "past" if past else "todo"
        if status == "todo" and current is None:
            status, current = "current", key
        steps.append({"key": key, "to": to, "status": status})
    foundation = {"steps": steps, "done": sum(1 for s in steps if s["status"] == "done"), "total": len(steps),
                  "complete": all(s["status"] in ("done", "past") for s in steps), "past": past}

    # The one next action.
    due = sum(practice.review_counts(db, user).values())
    if current is not None:
        nxt = {"kind": "foundation", "key": current, "to": next(s["to"] for s in steps if s["key"] == current)}
    elif due >= REVIEW_FIRST_AT:
        nxt = {"kind": "review", "key": "review", "to": "/review", "count": due}
    elif state.exam_level is not None:
        nxt = {"kind": "exam", "key": "exam", "to": f"/exam/{state.exam_level}", "level": state.exam_level}
    elif state.current is not None:
        nxt = {"kind": "lesson", "key": "lesson", "to": f"/lessons/{state.current.lesson.id}",
               "lesson_id": state.current.lesson.id, "title": state.current.lesson.title, "level": state.current.level}
    else:
        nxt = {"kind": "stories", "key": "stories", "to": "/stories"}

    # HSK 1-9 as stages, with the learner's real progress in each.
    from app.services import books as books_lib
    from app.services import stories as stories_svc

    summaries = {s["level"]: s for s in lesson_path.level_summaries(state)}
    read = stories_svc.read_slugs(db, user)
    levels = []
    for lvl in range(1, 10):
        s = summaries.get(lvl, {})
        lib = [b for b in books_lib.all_books() if b["level"] == lvl]
        levels.append({
            "level": lvl, "stage": STAGE_OF[lvl],
            "lessons_done": s.get("completed", 0), "lessons_total": s.get("total", 0),
            "stories_read": sum(1 for st in lib if st["slug"] in read), "stories_total": len(lib),
            "exam_passed": lvl in state.exams_passed,
            "status": ("current" if lvl == min(level, 7) or (lvl > 7 and level >= 7 and s.get("completed", 0))
                       else "done" if lvl < level else "ahead"),
        })

    def suggested(rule: str) -> bool:
        return {"start": True, "first_lesson": ev["lessons"] >= 1, "any_activity": ev["any"],
                "words_20": ev["known_words"] >= 20, "level_2": level >= 2}[rule]

    features = [{"key": k, "to": to, "suggested": suggested(rule)} for k, to, rule in FEATURES]
    return {
        "level": level, "stage": "foundation" if (not foundation["complete"] and not past) else STAGE_OF[level],
        "foundation": foundation, "next": nxt, "levels": levels, "features": features,
        "due_reviews": due, "known_words": ev["known_words"], "lessons_done": ev["lessons"],
    }
