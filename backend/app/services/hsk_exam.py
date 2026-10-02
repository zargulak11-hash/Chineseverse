"""HSK level final exams: the gate between one HSK level and the next.

Finishing every lesson of a level puts the learner in front of its exam
(services/lesson_path.py: PathState.exam_level); only a passed exam opens
the next level. Everything is decided here, on the server:

- eligibility: the exam of the level the path is gated on, nothing else;
- the questions: built from the vocabulary and grammar that level's
  lessons taught (practice.lesson_items), through the same question engine
  as practice -- the browser gets option ids and labels, never the answer;
- the answers: option ids, stored as given; correctness is never returned
  per question;
- the clock: expires_at, checked on every access;
- the result: score computed from the stored answers, PASS_SCORE fixed here.

Integrity: an attempt is a one-shot protected session. Leaving the exam page,
hiding it (switching tab/window), closing or reloading it, or opening it
again by URL ends it as "invalidated" with score 0 -- the page reports what
it can see (POST /violation, also with keepalive on page hide), and the
server invalidates any in-progress attempt that is reopened (GET), which is
what a reload or a second tab does even if the report never arrived. The
page must also stay present: while it is visible and focused it sends a
heartbeat every few seconds, and any contact after more than
PRESENCE_TIMEOUT of silence -- the page closed, reloaded, navigated away,
crashed, or was put in the background, whether or not its report got
through -- ends the attempt as invalidated with 0, as does a ghost attempt
found silent later. An attempt nobody submits expires (score 0) once its
time is up. A determined user could still script heartbeats and answers;
the server-side rules (no reopening, one active attempt, presence, fixed
clock, server grading) are what a page that was really left cannot get
past.

Lesson progress is never touched: a failed exam leaves every completed
lesson completed.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from types import SimpleNamespace

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.services import lesson_path, practice

PASS_SCORE = 80.0          # percent of questions answered correctly
QUESTION_COUNT = 20
GRAMMAR_SHARE = 6          # up to this many grammar questions, the rest vocabulary
TIME_LIMIT = timedelta(minutes=20)
# The exam page beats every HEARTBEAT seconds (frontend pages/Exam.jsx);
# six missed beats is not a network hiccup, it is a page that is gone.
PRESENCE_TIMEOUT = timedelta(seconds=30)
VIOLATIONS = {"left_page", "hidden", "navigation", "closed", "reopened", "window_blur", "lost_contact"}

IN_PROGRESS, PASSED, FAILED, INVALIDATED, EXPIRED = "in_progress", "passed", "failed", "invalidated", "expired"


class ExamError(Exception):
    def __init__(self, status: int, detail: str, code: str, **extra):
        super().__init__(detail)
        self.status, self.detail, self.code, self.extra = status, detail, code, extra


def level_material(db: Session, level: int) -> list[tuple[str, object]]:
    """Every vocabulary word and grammar point the lessons of this (display)
    level teach, once each."""
    seen: set[tuple[str, int]] = set()
    out = []
    for lesson, lvl in lesson_path.ordered_lessons(db):
        if lvl != level:
            continue
        items = practice.lesson_items(db, lesson)
        for item_type, rows in (("vocab", items["vocab"]), ("grammar", items["grammar"])):
            for row in rows:
                if (item_type, row.id) not in seen and practice._usable(item_type, row):
                    seen.add((item_type, row.id))
                    out.append((item_type, row))
    return out


def _finish(attempt: models.HSKExamAttempt, status: str, now: datetime) -> None:
    attempt.status = status
    attempt.finished_at = now
    if status in (INVALIDATED, EXPIRED):
        attempt.correct, attempt.score = 0, 0.0


def expire_stale(db: Session, user: models.User) -> None:
    """An attempt whose time is up and was never submitted fails with 0 --
    also what happens when the browser crashed or vanished mid-exam."""
    now = datetime.utcnow()
    changed = False
    for attempt in db.query(models.HSKExamAttempt).filter_by(user_id=user.id, status=IN_PROGRESS).all():
        if attempt.expires_at <= now:
            _finish(attempt, EXPIRED, now)
            changed = True
        elif _silent(attempt, now):
            _lost(attempt, now)
            changed = True
    if changed:
        db.commit()


def _silent(attempt: models.HSKExamAttempt, now: datetime) -> bool:
    return now - (attempt.last_seen_at or attempt.started_at) > PRESENCE_TIMEOUT


def _lost(attempt: models.HSKExamAttempt, now: datetime) -> None:
    attempt.violations = list(attempt.violations or []) + [{"reason": "lost_contact", "at": now.isoformat() + "Z"}]
    _finish(attempt, INVALIDATED, now)


def result(attempt: models.HSKExamAttempt) -> dict:
    return {
        "id": attempt.id,
        "level": attempt.level,
        "status": attempt.status,
        "total": attempt.total,
        "correct": attempt.correct,
        "incorrect": None if attempt.correct is None else attempt.total - attempt.correct,
        "score": attempt.score,
        "passed": attempt.status == PASSED,
        "pass_score": PASS_SCORE,
        "violations": [v.get("reason") for v in (attempt.violations or [])],
        "started_at": attempt.started_at.isoformat() + "Z",
        "finished_at": attempt.finished_at.isoformat() + "Z" if attempt.finished_at else None,
    }


def render(db: Session, attempt: models.HSKExamAttempt, locale: str) -> dict:
    """The exam as the browser may see it: prompts and options only. The
    renderer is always given empty answers, so no correct id or answer card
    is ever included, even for questions already answered."""
    fake = SimpleNamespace(id=attempt.id, source="exam", hsk_level=attempt.level, lesson_id=None,
                           questions=attempt.questions, answers=[None] * len(attempt.questions),
                           completed_at=None, score=None)
    questions = practice.render_session(db, fake, locale)["questions"]
    for q in questions:
        q.pop("answer", None)
    return {
        **result(attempt),
        "expires_at": attempt.expires_at.isoformat() + "Z",
        "seconds_left": max(0, int((attempt.expires_at - datetime.utcnow()).total_seconds())),
        "answered": sum(1 for a in attempt.answers if a is not None),
        "questions": questions,
    }


def overview(db: Session, user: models.User) -> dict:
    expire_stale(db, user)
    state = lesson_path.path_state(db, user)
    attempts = db.query(models.HSKExamAttempt).filter_by(user_id=user.id).all()
    levels = []
    for summary in lesson_path.level_summaries(state):
        mine = [a for a in attempts if a.level == summary["level"]]
        scores = [a.score for a in mine if a.score is not None]
        levels.append({
            "level": summary["level"],
            "exam": summary["exam"],
            "lessons_completed": summary["completed"],
            "lessons_total": summary["total"],
            "attempts": len(mine),
            "best_score": max(scores) if scores else None,
        })
    active = next((a for a in attempts if a.status == IN_PROGRESS), None)
    return {
        "exam_level": state.exam_level,
        "pass_score": PASS_SCORE,
        "question_count": QUESTION_COUNT,
        "time_limit_seconds": int(TIME_LIMIT.total_seconds()),
        "active_attempt_id": active.id if active else None,
        "levels": levels,
    }


def start(db: Session, user: models.User, level: int, locale: str) -> models.HSKExamAttempt:
    expire_stale(db, user)
    state = lesson_path.path_state(db, user)
    if state.exam_level != level:
        raise ExamError(403, "This exam is not open: finish the level's lessons first", "exam_locked",
                        exam_level=state.exam_level)
    active = db.query(models.HSKExamAttempt).filter_by(user_id=user.id, status=IN_PROGRESS).first()
    if active is not None:
        raise ExamError(409, "An exam attempt is already in progress", "exam_in_progress", attempt_id=active.id)

    material = level_material(db, level)
    rng = random.Random()
    grammar = [m for m in material if m[0] == "grammar"]
    vocab = [m for m in material if m[0] == "vocab"]
    rng.shuffle(grammar)
    rng.shuffle(vocab)
    picked = grammar[:GRAMMAR_SHARE]
    picked += vocab[:QUESTION_COUNT - len(picked)]
    picked += grammar[GRAMMAR_SHARE:GRAMMAR_SHARE + QUESTION_COUNT - len(picked)]
    rng.shuffle(picked)
    translated = (
        {ct: practice._translated_ids(db, ct, locale) for ct in ("vocab_word", "hanzi")}
        if locale in ("ru", "tg") else None
    )
    questions = []
    for i, (item_type, row) in enumerate(picked):
        q = practice._question(db, item_type, row, i, rng, translated)
        if q:
            questions.append(q)
    if len(questions) < 5:
        raise ExamError(422, "Not enough taught material at this level to build an exam", "exam_unavailable")

    now = datetime.utcnow()
    attempt = models.HSKExamAttempt(
        user_id=user.id, level=level, status=IN_PROGRESS, questions=questions,
        answers=[None] * len(questions), total=len(questions), violations=[],
        started_at=now, expires_at=now + TIME_LIMIT, last_seen_at=now,
    )
    db.add(attempt)
    try:
        db.commit()
    except IntegrityError:
        # Two tabs starting at the same instant: the unique index on the
        # active attempt lets exactly one through.
        db.rollback()
        active = db.query(models.HSKExamAttempt).filter_by(user_id=user.id, status=IN_PROGRESS).first()
        raise ExamError(409, "An exam attempt is already in progress", "exam_in_progress",
                        attempt_id=active.id if active else None)
    db.refresh(attempt)
    return attempt


def _require_active(db: Session, attempt: models.HSKExamAttempt) -> None:
    """Every contact from the exam page: the attempt must still be running,
    in time, and the page must have stayed present. A contact counts as a
    sign of life for the next one."""
    now = datetime.utcnow()
    if attempt.status == IN_PROGRESS and attempt.expires_at <= now:
        _finish(attempt, EXPIRED, now)
        db.commit()
    elif attempt.status == IN_PROGRESS and _silent(attempt, now):
        _lost(attempt, now)
        db.commit()
    if attempt.status != IN_PROGRESS:
        raise ExamError(409, "This exam attempt is over", "exam_over", result=result(attempt))
    attempt.last_seen_at = now


def heartbeat(db: Session, attempt: models.HSKExamAttempt) -> dict:
    _require_active(db, attempt)
    db.commit()
    return {"status": attempt.status, "seconds_left": max(0, int((attempt.expires_at - datetime.utcnow()).total_seconds()))}


def answer(db: Session, attempt: models.HSKExamAttempt, index: int, choice_id: int) -> dict:
    _require_active(db, attempt)
    if not 0 <= index < len(attempt.questions):
        raise ExamError(422, "No such question", "exam_bad_question")
    if choice_id not in attempt.questions[index]["option_ids"]:
        raise ExamError(422, "That option was not offered for this question", "exam_bad_option")
    answers = list(attempt.answers)  # reassign so the JSON column is marked dirty
    answers[index] = choice_id
    attempt.answers = answers
    db.commit()
    # Nothing about correctness: that is decided only when the exam is submitted.
    return {"answered": sum(1 for a in answers if a is not None), "total": attempt.total}


def submit(db: Session, attempt: models.HSKExamAttempt) -> dict:
    _require_active(db, attempt)
    correct = sum(1 for q, a in zip(attempt.questions, attempt.answers) if a is not None and a == q["item_id"])
    attempt.correct = correct
    attempt.score = round(correct / attempt.total * 100, 1) if attempt.total else 0.0
    _finish(attempt, PASSED if attempt.score >= PASS_SCORE else FAILED, datetime.utcnow())
    db.commit()
    return result(attempt)


def violate(db: Session, attempt: models.HSKExamAttempt, reason: str) -> dict:
    """An integrity rule was broken: the attempt ends now with score 0. A
    finished attempt is left as it is."""
    if attempt.status == IN_PROGRESS:
        now = datetime.utcnow()
        attempt.violations = list(attempt.violations or []) + [{"reason": reason, "at": now.isoformat() + "Z"}]
        _finish(attempt, INVALIDATED, now)
        db.commit()
    return result(attempt)
