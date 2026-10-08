"""Mix-up memory: the pairs of words and characters THIS learner takes for
each other, and whether they can tell them apart yet.

Every graded multiple-choice answer is already stored on its practice
session -- the question's target, the options offered and the option the
learner actually picked. A wrong pick between two curriculum items is a
real mix-up ("asked for 觉得, chose 认为"). This module reads those answers,
in the order they happened, and keeps per pair:

  confused     how many times one was picked when the other was asked
  told_apart   correct answers since the last mix-up IN WHICH THE OTHER ONE
               WAS AMONG THE OPTIONS -- only then did the learner really
               choose between the two
  status       "active" until told apart RESOLVE_AFTER times in a row of
               such answers, then "resolved"; a new mix-up makes it active
               again (with the count back at zero)

It turns them back into learning, so the mistake is the lesson:

  * any vocabulary / character round offers a learner's own mix-up
    partner among the wrong options of that item (partners_by_item), so
    the two keep meeting until they are told apart;
  * the "mixups" practice round (practice.build_session) is a drill made
    only of active pairs, each item asked with its partner on screen;
  * the mistake notebook, today's plan and the companion read the same
    pairs (pairs()).

Nothing is stored here and nothing is guessed: a pair exists only because
the learner made that exact choice. Only the last WINDOW_DAYS of rounds are
read, like the companion's memory (companion_memory.CONFUSION_WINDOW_DAYS).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app import models

WINDOW_DAYS = 60
# Told apart this many times (with both on screen) since the last mix-up:
# the pair is resolved.
RESOLVE_AFTER = 3
# A single wrong pick may be a guess; a pair shown in the notebook, drilled,
# or put on today's plan has been mixed up at least this often. A partner
# offered among the options in ordinary rounds needs only one real mix-up --
# that costs the learner nothing and is exactly the comparison they missed.
NOTEBOOK_MIN = 2
# Question types whose options are rows of the same table (the same set as
# companion_memory._CONFUSABLE): only there is a wrong pick a confusion
# between two curriculum items.
CONFUSABLE = {"meaning_to_word", "word_to_meaning", "listen_to_word", "char_to_meaning", "char_to_pinyin"}


def _sessions(db: Session, user: models.User) -> list[models.PracticeSession]:
    since = datetime.utcnow() - timedelta(days=WINDOW_DAYS)
    return (
        db.query(models.PracticeSession)
        .filter(models.PracticeSession.user_id == user.id, models.PracticeSession.created_at >= since)
        .order_by(models.PracticeSession.created_at, models.PracticeSession.id)
        .all()
    )


def _track(sessions: list[models.PracticeSession]) -> dict[tuple[str, int, int], dict]:
    """(item_type, lo_id, hi_id) -> {confused, told_apart, last, qtype},
    replaying the answers in the order they were given."""
    pairs: dict[tuple[str, int, int], dict] = {}
    for s in sessions:
        for q, a in zip(s.questions or [], s.answers or []):
            if not a or q.get("type") not in CONFUSABLE or q.get("item_type") not in ("vocab", "hanzi"):
                continue
            target, item_type = q.get("item_id"), q["item_type"]
            if not a.get("correct"):
                picked = a.get("choice_id")
                if picked is None or picked == target:
                    continue
                lo, hi = sorted((target, picked))
                p = pairs.setdefault((item_type, lo, hi), {"confused": 0, "told_apart": 0, "last": None,
                                                          "qtype": q["type"]})
                p["confused"] += 1
                p["told_apart"] = 0
                p["last"] = a.get("answered_at")
                p["qtype"] = q["type"]
                continue
            for other in q.get("option_ids") or []:
                if other == target:
                    continue
                lo, hi = sorted((target, other))
                p = pairs.get((item_type, lo, hi))
                if p is not None:
                    p["told_apart"] += 1
    return pairs


def _status(p: dict) -> str:
    return "resolved" if p["told_apart"] >= RESOLVE_AFTER else "active"


def partners_by_item(db: Session, user: models.User) -> dict[tuple[str, int], list[int]]:
    """(item_type, item id) -> ids it is still mixed up with, most-confused
    first. Feeds the wrong options of ordinary rounds."""
    out: dict[tuple[str, int], list[tuple[int, int]]] = {}
    for (item_type, lo, hi), p in _track(_sessions(db, user)).items():
        if _status(p) != "active":
            continue
        out.setdefault((item_type, lo), []).append((p["confused"], hi))
        out.setdefault((item_type, hi), []).append((p["confused"], lo))
    return {k: [i for _n, i in sorted(v, reverse=True)] for k, v in out.items()}


def active_pairs(db: Session, user: models.User) -> list[dict]:
    """Pairs worth drilling now: active and mixed up NOTEBOOK_MIN+ times,
    most-confused (then most recent) first."""
    return [p for p in pairs(db, user, labels=False) if p["status"] == "active"]


def pairs(db: Session, user: models.User, locale: str = "en", labels: bool = True) -> list[dict]:
    """Every pair mixed up NOTEBOOK_MIN+ times in the window: active ones
    first (most confused, then most recent), resolved ones after."""
    tracked = _track(_sessions(db, user))
    rows = []
    for (item_type, lo, hi), p in tracked.items():
        if p["confused"] < NOTEBOOK_MIN:
            continue
        rows.append({"item_type": item_type, "a_id": lo, "b_id": hi, "qtype": p["qtype"],
                     "confused": p["confused"], "told_apart": p["told_apart"],
                     "resolve_after": RESOLVE_AFTER, "status": _status(p), "last_confused_at": p["last"]})
    # Two stable sorts: most recent first, then active before resolved and
    # most-confused first (ties keep the recency order).
    rows.sort(key=lambda r: r["last_confused_at"] or "", reverse=True)
    rows.sort(key=lambda r: (r["status"] != "active", -r["confused"]))
    if labels and rows:
        _label(db, rows, locale)
    return rows


def _label(db: Session, rows: list[dict], locale: str) -> None:
    """Each side as hanzi, pinyin and its meaning in the learner's language
    (the same labels a practice round shows)."""
    from app.services import practice

    pseudo = [{"item_type": r["item_type"], "option_ids": [r["a_id"], r["b_id"]]} for r in rows]
    names = practice._labels(db, pseudo, locale)
    for r in rows:
        for side in ("a", "b"):
            row = practice._row(db, r["item_type"], r[f"{side}_id"])
            r[side] = practice._item_card(r["item_type"], row, names) if row is not None else None
    rows[:] = [r for r in rows if r["a"] and r["b"]]
