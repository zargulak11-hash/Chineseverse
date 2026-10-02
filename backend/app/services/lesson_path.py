"""The sequential lesson path: the server-side authority on which lessons a
learner has completed, which one is current, and which are still locked.

Lessons used to be a free catalogue -- any lesson of HSK 1-9 could be opened
and practiced in any order, and /api/progress let the client write
status="completed" for itself. Now every lesson read (/api/lessons/{id},
/items), every lesson practice round and every lesson completion goes
through this module, so hiding a link in React is never what keeps a lesson
locked.

Order: HSK level (the shared 7-9 band split into its three real stages
exactly like hsk_band.display_level_for_row does), then order_index, then
id -- the same order the lesson lists already used.

Steps: only lessons with a real practice round (practice.lesson_round_items)
are steps a learner must pass. A reading-only lesson has no round, so it
could never be completed; it opens with its position instead of blocking
everyone behind it forever.

Current lesson: the first step AFTER the furthest lesson the learner has
completed. For anyone who learns on the path this is simply "the first
unfinished step". It also keeps existing progress: a learner who completed
lessons 1-10 before the path existed resumes at 11, and a learner whose old
completions have gaps keeps those earlier lessons open ("available") rather
than being sent back. Nothing here writes or resets progress rows.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app import models
from app.services.hsk_band import split_thirds
from app.services.practice import lesson_round_items

COMPLETED, CURRENT, AVAILABLE, LOCKED = "completed", "current", "available", "locked"
LOCKED_DETAIL = "This lesson is locked. Complete the previous lesson first."


@dataclass
class PathEntry:
    lesson: models.Lesson
    level: int
    practicable: bool
    status: str = LOCKED
    score: int | None = None


@dataclass
class PathState:
    entries: list[PathEntry] = field(default_factory=list)
    current: PathEntry | None = None

    def entry(self, lesson_id: int) -> PathEntry | None:
        return next((e for e in self.entries if e.lesson.id == lesson_id), None)

    def is_open(self, lesson_id: int) -> bool:
        e = self.entry(lesson_id)
        return e is not None and e.status != LOCKED

    def after(self, lesson_id: int) -> PathEntry | None:
        """The next step after `lesson_id` (what "continue" leads to)."""
        ids = [e.lesson.id for e in self.entries]
        if lesson_id not in ids:
            return None
        return next((e for e in self.entries[ids.index(lesson_id) + 1:] if e.practicable), None)


def ordered_lessons(db: Session) -> list[tuple[models.Lesson, int]]:
    """Every lesson with its display HSK level, in path order."""
    levels = {lvl.id: lvl for lvl in db.query(models.HSKLevel).all()}
    lessons = db.query(models.Lesson).all()
    stage: dict[int, int] = {}
    for lvl in levels.values():
        if lvl.is_advanced_band:
            ids = sorted(l.id for l in lessons if l.hsk_level_id == lvl.id)
            for i, chunk in enumerate(split_thirds(ids)):
                stage.update({lid: 7 + i for lid in chunk})

    def display(lesson: models.Lesson) -> int:
        if lesson.id in stage:
            return stage[lesson.id]
        lvl = levels.get(lesson.hsk_level_id)
        # A lesson with no level sorts after HSK 9 rather than jumping the queue.
        return lvl.level if lvl else 10

    pairs = [(l, display(l)) for l in lessons]
    pairs.sort(key=lambda p: (p[1], p[0].order_index or 0, p[0].id))
    return pairs


# Which lessons have a practice round is the slow part (two queries per
# lesson, ~0.5s for the whole curriculum) and it only changes when content
# does, so it is cached per process. The key covers what the rule reads:
# every lesson's level and text, plus the vocabulary and grammar row counts;
# any admin edit to a lesson, or a content seed, recomputes it.
_practicable_cache: dict = {"key": None, "ids": frozenset()}


def _practicable_ids(db: Session, lessons: list[models.Lesson]) -> frozenset[int]:
    key = hash((
        tuple((l.id, l.hsk_level_id, l.summary, l.content) for l in lessons),
        db.query(models.VocabularyWord).count(),
        db.query(models.GrammarTopic).count(),
    ))
    if _practicable_cache["key"] != key:
        ids = frozenset(l.id for l in lessons if lesson_round_items(db, l))
        _practicable_cache.update(key=key, ids=ids)
    return _practicable_cache["ids"]


def path_state(db: Session, user: models.User) -> PathState:
    pairs = ordered_lessons(db)
    progress = {p.lesson_id: p for p in db.query(models.Progress).filter_by(user_id=user.id)}
    done = {lid for lid, p in progress.items() if p.status == "completed"}
    practicable = _practicable_ids(db, [l for l, _ in pairs])
    entries = [PathEntry(lesson=l, level=lvl, practicable=l.id in practicable) for l, lvl in pairs]

    furthest = max((i for i, e in enumerate(entries) if e.lesson.id in done), default=-1)
    frontier = next((i for i in range(furthest + 1, len(entries)) if entries[i].practicable), len(entries))

    state = PathState(entries=entries)
    for i, e in enumerate(entries):
        p = progress.get(e.lesson.id)
        e.score = p.score if p else None
        if e.lesson.id in done:
            e.status = COMPLETED
        elif i == frontier:
            e.status = CURRENT
            state.current = e
        elif i < frontier:
            e.status = AVAILABLE
        else:
            e.status = LOCKED
    return state


def path_level(db: Session, user: models.User) -> int:
    """The HSK level the learner has really reached on the path: the level of
    their current lesson, or the last level once every step is completed.
    Display levels, so the shared 7-9 band reports 7, 8 or 9."""
    state = path_state(db, user)
    if state.current is not None:
        return state.current.level
    steps = [e for e in state.entries if e.practicable]
    if steps and all(e.status == COMPLETED for e in steps):
        return max(e.level for e in steps)
    return 1


def level_summaries(state: PathState) -> list[dict]:
    """Per-HSK-level progress along the path, in level order."""
    by_level: dict[int, list[PathEntry]] = {}
    for e in state.entries:
        by_level.setdefault(e.level, []).append(e)
    out = []
    for level, entries in by_level.items():
        steps = [e for e in entries if e.practicable]
        if state.current is not None and state.current.level == level:
            status = CURRENT
        elif all(e.status == LOCKED for e in entries):
            status = LOCKED
        elif all(e.status == COMPLETED for e in steps):
            status = COMPLETED
        else:
            status = AVAILABLE
        out.append({
            "level": level,
            "status": status,
            "completed": sum(1 for e in steps if e.status == COMPLETED),
            "total": len(steps),
            "entries": entries,
        })
    return out


def locked_payload(state: PathState) -> dict:
    """Body of the 403 a locked lesson returns: `code` lets the page explain
    it in the learner's language (as duels do), `current_lesson_id` lets it
    point at the lesson to study instead."""
    return {
        "detail": LOCKED_DETAIL,
        "code": "lesson_locked",
        "current_lesson_id": state.current.lesson.id if state.current else None,
    }
