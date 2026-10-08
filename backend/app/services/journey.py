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
SLIPPING_FIRST_AT = 3  # ... or this many words/characters they KNEW fading (srs.is_slipping)
MIXUP_FIRST_AT = 3  # a pair confused this often comes before new material (services/mixups.py)
FRESH_READING_DAYS = 2  # a book opened this recently is "continue reading" before the next lesson
WEAK_SKILL_BELOW = 50.0  # a practised Learning Compass skill this low is worth a step of its own

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


def _slipping_count(db: Session, user: models.User) -> int:
    """Words and characters the learner knew that are slipping
    (services/srs.is_slipping): known, and SLIP_AFTER past their review."""
    from datetime import datetime

    from app.services.srs import SLIP_AFTER

    cut = datetime.utcnow() - SLIP_AFTER
    total = 0
    for rec_model in (models.UserVocabulary, models.UserHanzi):
        total += (db.query(rec_model.id)
                  .filter(rec_model.user_id == user.id, rec_model.status.in_(("reviewing", "mastered")),
                          rec_model.next_review_at.isnot(None), rec_model.next_review_at <= cut)
                  .count())
    return total


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


# A Learning Compass skill -> where it is practised, and which practice
# source (or special record) counts as having practised it today.
SKILL_PRACTICE = {
    "vocabulary": ("/practice?source=vocab&level={level}", "vocab"),
    "reaction_speed": ("/practice?source=vocab&level={level}", "vocab"),
    "grammar": ("/practice?source=grammar&level={level}", "grammar"),
    "writing": ("/practice?source=hanzi&level={level}", "hanzi"),
    "tones": ("/foundation", "tones"),
    "listening": ("/sound-world", "sound"),
    "speaking": ("/real-chinese", "voice"),
    "reading": ("/stories", "story"),
    "memory": ("/review", "review"),
}
# The practice source that does each kind of "next step".
NEXT_SOURCE = {"tones": "tones", "characters": "hanzi", "first_lesson": "lesson", "sentence": "sentence",
               "listen": "sound", "speak": "voice", "story": "story", "review": "review",
               "lesson": "lesson", "stories": "story", "exam": "exam", "mixups": "mixups",
               "continue": "story", "skill": ""}


def _reading(db: Session, user: models.User, level: int, locale: str) -> dict | None:
    """The book the learner is in the middle of (their last-touched
    unfinished StoryProgress whose book is open at their level), with where
    the bookmark is. None when they are not reading anything."""
    from datetime import datetime

    from app.services import books as books_lib
    from app.services import stories as stories_svc

    by_slug = {b["slug"]: b for b in books_lib.all_books()}
    rows = (db.query(models.StoryProgress)
            .filter(models.StoryProgress.user_id == user.id, models.StoryProgress.completed_at.is_(None))
            .order_by(models.StoryProgress.updated_at.desc()).limit(5).all())
    for row in rows:
        book = by_slug.get(row.slug)
        if book is None or stories_svc.gate(book) > level:
            continue
        title = book["title"].get(locale) or book["title"]["en"]
        return {"slug": row.slug, "chapter": row.chapter + 1, "title": title, "title_zh": book["title"]["zh"],
                "to": f"/stories/{row.slug}/read/{row.chapter + 1}",
                "days": (datetime.utcnow() - row.updated_at).days}
    return None


def today(db: Session, user: models.User, level: int, nxt: dict, due: int, foundation_complete: bool,
          mixed: list[dict] | None = None, reading: dict | None = None) -> dict:
    """Today's plan: at most four real tasks, each with why it is suggested,
    ticked off only by what the learner really did today (UTC day, the same
    day the dashboard's minutes use). A brand-new learner gets the one next
    step and nothing else -- never a list of chores they can't start yet.

    Nothing is ever marked done for them, and "done today" counts are read
    from today's records (completed rounds, voice turns, reading), never
    estimated."""
    from datetime import datetime, time as dtime

    from sqlalchemy import func

    start = datetime.combine(datetime.utcnow().date(), dtime.min)
    rounds = (db.query(models.PracticeSession)
              .filter(models.PracticeSession.user_id == user.id, models.PracticeSession.completed_at >= start).all())
    did = {s.source for s in rounds}
    if db.query(models.VoiceAttempt.id).filter(models.VoiceAttempt.user_id == user.id,
                                              models.VoiceAttempt.created_at >= start).first():
        did.add("voice")
    if db.query(models.StoryProgress.id).filter(models.StoryProgress.user_id == user.id,
                                               models.StoryProgress.updated_at >= start).first():
        did.add("story")
    if db.query(models.HSKExamAttempt.id).filter(models.HSKExamAttempt.user_id == user.id,
                                                models.HSKExamAttempt.finished_at >= start).first():
        did.add("exam")

    tasks: list[dict] = []
    if due > 0 or "review" in did:
        # A review round finished today counts; what is still due is shown.
        tasks.append({"key": "review", "to": "/review", "count": due, "done": "review" in did})
    if nxt.get("kind") != "review":
        tasks.append({"key": "learn", "to": nxt["to"], "next": nxt,
                      "done": NEXT_SOURCE.get(nxt.get("key"), "") in did})
    # Words or characters the learner keeps taking for each other: a short
    # drill of exactly those pairs (services/mixups.py) beats a generic one.
    # (Not twice when the drill already IS the next step.)
    mixed = mixed or []
    if (mixed or "mixups" in did) and nxt.get("kind") != "mixups":
        tasks.append({"key": "mixups", "to": "/practice?source=mixups", "count": len(mixed),
                      "done": "mixups" in did})
    practised = [s for s in user.user_skills if s.skill and (s.mastery or 0) > 0]
    weakest = min(practised, key=lambda s: s.mastery) if practised else None
    if weakest is not None and weakest.mastery < 70 and weakest.skill.code in SKILL_PRACTICE:
        route, source = SKILL_PRACTICE[weakest.skill.code]
        if not any(t["to"] == route.format(level=level) for t in tasks):
            tasks.append({"key": "weak", "skill": weakest.skill.code, "mastery": round(weakest.mastery),
                          "to": route.format(level=level), "done": source in did})
    if foundation_complete and not any(t["to"].startswith("/stories") for t in tasks):
        # Back into the book they are reading, when there is one.
        tasks.append({"key": "read", "to": reading["to"] if reading else "/stories", "done": "story" in did,
                      "book": reading["title"] if reading else None})
    tasks = tasks[:4]

    minutes = (db.query(func.coalesce(func.sum(models.ActivityEvent.minutes), 0.0))
               .filter(models.ActivityEvent.user_id == user.id, models.ActivityEvent.created_at >= start).scalar())
    words = (db.query(models.UserVocabulary.id)
             .filter(models.UserVocabulary.user_id == user.id, models.UserVocabulary.last_reviewed_at >= start).count())
    return {
        "tasks": tasks,
        "left": sum(1 for t in tasks if not t["done"]),
        "rounds": len(rounds),
        "words": words,
        "minutes": round(minutes or 0),
        "goal_minutes": user.profile.daily_goal_minutes if user.profile else 10,
    }


def journey(db: Session, user: models.User, locale: str = "en") -> dict:
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
    # total + mistakes, exactly as the dashboard counts them. This used to sum
    # every value of review_counts -- which holds the per-type counts AND
    # their "total" -- so each due item counted twice: "Review 16" for 8, and
    # review jumped ahead of new lessons at half the intended backlog.
    counts = practice.review_counts(db, user)
    due = counts["total"] + counts["mistakes"]
    slipping = _slipping_count(db, user)
    from app.services import mixups

    mixed = [p for p in mixups.pairs(db, user, locale) if p["status"] == "active"]
    reading = _reading(db, user, level, locale)
    practised = [s for s in user.user_skills if s.skill and (s.mastery or 0) > 0]
    weakest = min(practised, key=lambda s: s.mastery) if practised else None

    # Each step carries the learner's own numbers that justify it, so the
    # page can say WHY (the pair they keep confusing, how many words are
    # fading), never a generic line.
    if current is not None:
        nxt = {"kind": "foundation", "key": current, "to": next(s["to"] for s in steps if s["key"] == current)}
    elif due >= REVIEW_FIRST_AT or slipping >= SLIPPING_FIRST_AT:
        nxt = {"kind": "review", "key": "review", "to": "/review", "count": due, "slipping": slipping}
    elif mixed and mixed[0]["confused"] >= MIXUP_FIRST_AT:
        top = mixed[0]
        nxt = {"kind": "mixups", "key": "mixups", "to": "/practice?source=mixups",
               "a": top["a"]["hanzi"], "b": top["b"]["hanzi"], "count": top["confused"], "pairs": len(mixed)}
    elif state.exam_level is not None:
        nxt = {"kind": "exam", "key": "exam", "to": f"/exam/{state.exam_level}", "level": state.exam_level}
    elif reading is not None and reading["days"] < FRESH_READING_DAYS:
        nxt = {"kind": "continue", "key": "continue", **reading}
    elif state.current is not None:
        from app.services.localization import load_translations, tr

        cur = state.current.lesson
        # In the learner's language (this used to send the English title).
        title = tr(load_translations(db, "lesson", [str(cur.id)], locale), cur.id, "title", cur.title)
        nxt = {"kind": "lesson", "key": "lesson", "to": f"/lessons/{cur.id}",
               "lesson_id": cur.id, "title": title, "level": state.current.level}
    elif reading is not None:
        nxt = {"kind": "continue", "key": "continue", **reading}
    elif weakest is not None and weakest.mastery < WEAK_SKILL_BELOW and weakest.skill.code in SKILL_PRACTICE:
        nxt = {"kind": "skill", "key": "skill", "skill": weakest.skill.code, "mastery": round(weakest.mastery),
               "to": SKILL_PRACTICE[weakest.skill.code][0].format(level=level)}
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
        "due_reviews": due, "slipping": slipping, "known_words": ev["known_words"], "lessons_done": ev["lessons"],
        "today": today(db, user, level, nxt, due, foundation["complete"] or past, mixed, reading),
    }
