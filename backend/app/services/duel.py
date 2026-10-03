"""Real 1-vs-1 duels between two users. The server is authoritative for
everything that decides the result.

Lifecycle
    pending   challenger sent a challenge; only the invited opponent can
              accept/decline, only the challenger can cancel. Lapses to
              "expired" after CHALLENGE_TTL.
    active    the opponent accepted. Both players get the SAME stored
              question set. Each player has their OWN clock: it starts when
              THEY open the duel (start_attempt) and ends at
              started_at + time_limit_seconds. Nothing the opponent does
              moves it. A player who never starts within PLAY_WINDOW is
              finished as "no_show".
    completed both attempts are finished (all answered, timed out,
              forfeited or no-show); the winner is computed here from the
              stored answers.
    declined / cancelled / expired   terminal; no questions are played.

Timing is derived from server timestamps only: a player's remaining time is
deadline - now, an answer's response time is answered_at minus the previous
answer (or the start). The client never sends a time, a score, a correctness
flag or a winner.

Questions come from the practice engine (services/practice.py): real HSK
vocabulary / Hanzi / grammar rows, stored as {type, item_type, item_id,
option_ids}; the browser only ever sends back an option id.

Timeouts are applied lazily: every read or write of a duel first runs
refresh(), which finishes whatever attempt is past its deadline and
finalizes the duel once both are finished. No background job is needed and
a player who closes the tab still gets a correct result.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from types import SimpleNamespace

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.services import notifications
from app.services import practice
from app.services.activity import log_activity
from app.services.avatars import photo_url
from app.services.gamification import check_achievements, progress_missions, progress_quests, user_rank

ENGINE = "practice_v1"
QUESTION_COUNT = 10
TIME_LIMIT_SECONDS = 150          # the same total budget for both players
CHALLENGE_TTL = timedelta(hours=24)
PLAY_WINDOW = timedelta(hours=24)  # after acceptance, to start one's attempt
ANSWER_GRACE = timedelta(milliseconds=1500)  # network latency, never more

POINTS_CORRECT = 10
POINTS_WRONG = 2                  # existing duel rule: an attempt is worth something
SPEED_BONUS_MAX = 8               # existing duel rule, now server-timed for every type
SPEED_BONUS_WINDOW_MS = 6000

OPEN_STATUSES = ("pending", "active")
TERMINAL_STATUSES = ("completed", "declined", "cancelled", "expired")

# focus -> question types used (all real practice-engine types)
FOCUS_TYPES = {
    "mix": [("vocab", "word_to_meaning"), ("vocab", "meaning_to_word"), ("hanzi", "char_to_meaning"),
            ("vocab", "listen_to_word"), ("hanzi", "char_to_pinyin")],
    "vocab": [("vocab", "word_to_meaning"), ("vocab", "meaning_to_word")],
    "listening": [("vocab", "listen_to_word")],
    "hanzi": [("hanzi", "char_to_meaning")],
    "tones": [("hanzi", "char_to_pinyin")],
    "grammar": [("grammar", "example_to_point")],
}


# Human-readable `detail` for every error code (the API returns both; the
# UI translates `code` and falls back to `detail`).
MESSAGES = {
    "not_found": "Duel not found",
    "not_allowed": "Only the other player can do that",
    "cannot_challenge_self": "You cannot challenge yourself",
    "opponent_not_found": "That player does not exist",
    "duel_already_open": "You already have an open duel with this player",
    "invalid_level": "HSK level must be between 1 and 9",
    "not_enough_content": "Not enough content at this level to build a duel",
    "not_started": "Start your attempt first",
    "no_such_question": "No such question",
    "already_answered": "This question was already answered",
    "out_of_order": "Answer the current question first",
    "invalid_option": "That option was not offered for this question",
    "time_up": "Your time is up",
    "already_finished": "You have already finished this duel",
}
_STATE_MESSAGES = {
    "not_pending": "This challenge is no longer pending ({status})",
    "not_active": "This duel is not in progress ({status})",
}


class DuelError(Exception):
    """status + a stable machine code (translated by the UI) + an English
    `detail` for anything that only shows the message."""

    def __init__(self, status: int, code: str):
        super().__init__(code)
        self.status = status
        self.code = code
        prefix, _, state = code.rpartition("_")
        if code in MESSAGES:
            self.detail = MESSAGES[code]
        elif prefix in _STATE_MESSAGES:
            self.detail = _STATE_MESSAGES[prefix].format(status=state)
        else:
            self.detail = code


def _now() -> datetime:
    return datetime.utcnow()


def is_legacy(duel: models.Duel) -> bool:
    return (duel.question_data or {}).get("engine") != ENGINE


def _questions(duel: models.Duel) -> list[dict]:
    return (duel.question_data or {}).get("questions", []) if not is_legacy(duel) else []


def side(duel: models.Duel, user_id: int) -> models.DuelParticipant | None:
    return next((p for p in duel.participants if p.user_id == user_id), None)


def other_side(duel: models.Duel, user_id: int) -> models.DuelParticipant | None:
    return next((p for p in duel.participants if p.user_id != user_id), None)


# --------------------------------------------------------------------------- loading

def load_for(db: Session, duel_id: int, user: models.User, lock: bool = True) -> models.Duel:
    """The duel, locked for this transaction, if `user` takes part in it.
    Anyone else gets the same 404 as a missing duel, so ids don't leak."""
    q = db.query(models.Duel).filter(models.Duel.id == duel_id)
    if lock:
        q = q.with_for_update()
    duel = q.first()
    if duel is None or side(duel, user.id) is None:
        raise DuelError(404, "not_found")
    return duel


# --------------------------------------------------------------------------- questions

def build_questions(db: Session, hsk_level: int, focus: str, count: int = QUESTION_COUNT,
                    seed: int | None = None) -> list[dict]:
    """One shared, deterministic (given the seed) question set from real
    curriculum rows at `hsk_level`. Not personalized to either player, so
    neither side gets an easier or more familiar set."""
    rng = random.Random(seed)
    plan = FOCUS_TYPES.get(focus) or FOCUS_TYPES["mix"]
    pools: dict[str, list] = {}
    for item_type in {it for it, _ in plan}:
        rows = [r for r in practice._level_rows(db, item_type, hsk_level) if practice._usable(item_type, r)]
        rng.shuffle(rows)
        pools[item_type] = rows
    out: list[dict] = []
    used: set[tuple[str, int]] = set()
    attempts = 0
    while len(out) < count and attempts < count * 6:
        item_type, qtype = plan[attempts % len(plan)]
        attempts += 1
        pool = pools.get(item_type) or []
        row = next((r for r in pool if (item_type, r.id) not in used), None)
        if row is None:
            continue
        used.add((item_type, row.id))
        distractors = practice._distractors(db, item_type, qtype, row, rng)
        if len(distractors) < 2:
            continue
        options = distractors + [row.id]
        rng.shuffle(options)
        q = {"type": qtype, "item_type": item_type, "item_id": row.id, "option_ids": options}
        if item_type == "grammar":
            q["prompt"] = practice._grammar_example(row)
        out.append(q)
    return out


def _render(db: Session, duel: models.Duel, user_id: int, locale: str, reveal: bool = False) -> list[dict]:
    """The question set rendered in the viewer's language, with only the
    viewer's OWN answers filled in (practice.render_session shape).
    reveal (completed duels only): unanswered questions get the answer card
    too, marked choice_id=None, so the review shows every correct answer."""
    qs = _questions(duel)
    mine = {a.question_index: a for a in duel.answers if a.user_id == user_id}
    unanswered = {"choice_id": None, "correct": False, "response_ms": None, "points": 0} if reveal else None
    answers = [
        {"choice_id": mine[i].choice_id, "correct": mine[i].correct, "response_ms": mine[i].response_ms,
         "points": mine[i].points} if i in mine else unanswered
        for i in range(len(qs))
    ]
    fake = SimpleNamespace(id=duel.id, source="duel", hsk_level=duel.hsk_level, lesson_id=None,
                           questions=qs, answers=answers, completed_at=None, score=None)
    return practice.render_session(db, fake, locale)["questions"]


# --------------------------------------------------------------------------- timing

def deadline(duel: models.Duel, p: models.DuelParticipant) -> datetime | None:
    if p.started_at is None:
        return None
    return p.started_at + timedelta(seconds=duel.time_limit_seconds or TIME_LIMIT_SECONDS)


def remaining_ms(duel: models.Duel, p: models.DuelParticipant, now: datetime) -> int:
    limit_ms = (duel.time_limit_seconds or TIME_LIMIT_SECONDS) * 1000
    if p.finished:
        return max(0, limit_ms - (p.time_used_ms or limit_ms))
    end = deadline(duel, p)
    if end is None:
        return limit_ms
    return max(0, int((end - now).total_seconds() * 1000))


def _finish(duel: models.Duel, p: models.DuelParticipant, reason: str, at: datetime) -> None:
    if p.finished:
        return
    limit_ms = (duel.time_limit_seconds or TIME_LIMIT_SECONDS) * 1000
    p.finished = True
    p.finish_reason = reason
    p.finished_at = at
    if p.started_at is None:
        p.time_used_ms = limit_ms
    else:
        p.time_used_ms = max(0, min(limit_ms, int((at - p.started_at).total_seconds() * 1000)))


def refresh(db: Session, duel: models.Duel, now: datetime | None = None) -> bool:
    """Applies everything that happens with time: challenge expiry, each
    player's timeout or no-show, and finalization. Returns True if changed."""
    now = now or _now()
    changed = False
    if duel.status == "pending" and duel.expires_at and now >= duel.expires_at:
        duel.status = "expired"
        duel.finished_at = duel.expires_at
        changed = True
    if duel.status == "active":
        for p in duel.participants:
            if p.finished:
                continue
            end = deadline(duel, p)
            if end is not None and now >= end + ANSWER_GRACE:
                _finish(duel, p, "timeout", end)
                changed = True
            elif end is None and duel.play_deadline and now >= duel.play_deadline:
                _finish(duel, p, "no_show", duel.play_deadline)
                changed = True
        if duel.participants and all(p.finished for p in duel.participants):
            _finalize(db, duel, now)
            changed = True
    return changed


# --------------------------------------------------------------------------- result

def _rank_key(p: models.DuelParticipant) -> tuple:
    """Higher is better: correct answers, then score, then less time used."""
    return (p.correct_count or 0, p.score or 0, -(p.time_used_ms or 0))


def decide(a: models.DuelParticipant, b: models.DuelParticipant) -> tuple[models.DuelParticipant | None, str]:
    """(winner or None for a draw, what decided it). Symmetric: the order of
    the arguments, roles and who finished first never matter."""
    if (a.correct_count or 0) != (b.correct_count or 0):
        return (a if a.correct_count > b.correct_count else b), "correct"
    if (a.score or 0) != (b.score or 0):
        return (a if a.score > b.score else b), "score"
    if (a.time_used_ms or 0) != (b.time_used_ms or 0):
        return (a if a.time_used_ms < b.time_used_ms else b), "time"
    return None, "draw"


def _finalize(db: Session, duel: models.Duel, now: datetime) -> None:
    if duel.status == "completed":
        return
    ps = list(duel.participants)
    if len(ps) == 2:
        winner, by = decide(ps[0], ps[1])
    else:  # the other account was deleted mid-duel
        winner, by = (ps[0] if ps else None), "correct"
    duel.status = "completed"
    duel.decided_by = by
    duel.winner_id = winner.user_id if winner is not None else None
    duel.finished_at = now
    for p in ps:
        u = db.get(models.User, p.user_id)
        if u is None:
            continue
        log_activity(db, u, "duel_finish")
        progress_quests(db, u, "duel", amount=1)   # "Finish 1 duel"
        if duel.winner_id == u.id:
            # The duel mission is "Win your first DNA Duel" -- it used to
            # advance for both players, loser included.
            progress_missions(db, u, "duel")
        opp = next((o for o in ps if o.user_id != p.user_id), None)
        notifications.create_duel_notification(
            db, notifications.DUEL_COMPLETED, db.get(models.User, opp.user_id) if opp else None, u, duel.id
        )
    db.flush()
    for p in ps:
        u = db.get(models.User, p.user_id)
        if u is not None:
            check_achievements(db, u)


# --------------------------------------------------------------------------- actions

def opponent_candidates(db: Session, user: models.User, q: str | None) -> list[models.User]:
    """People from the user's own social graph (following + followers); a
    search term reaches every account by username. Never the user, never
    the legacy AI sparring account."""
    if q:
        rows = (
            db.query(models.User)
            .filter(models.User.username.ilike(f"%{q.strip()}%"), models.User.id != user.id)
            .order_by(models.User.username)
            .limit(20)
            .all()
        )
    else:
        ids = {f.following_id for f in db.query(models.Follow).filter_by(follower_id=user.id)}
        ids |= {f.follower_id for f in db.query(models.Follow).filter_by(following_id=user.id)}
        ids.discard(user.id)
        rows = (
            db.query(models.User).filter(models.User.id.in_(ids or {0})).order_by(models.User.username).all()
            if ids else []
        )
    return [r for r in rows if r.is_active and not r.username.startswith("__")]


def open_duel_between(db: Session, a_id: int, b_id: int) -> models.Duel | None:
    mine = {p.duel_id for p in db.query(models.DuelParticipant).filter_by(user_id=a_id)}
    theirs = {p.duel_id for p in db.query(models.DuelParticipant).filter_by(user_id=b_id)}
    shared = mine & theirs
    if not shared:
        return None
    now = _now()
    for d in db.query(models.Duel).filter(models.Duel.id.in_(shared), models.Duel.status.in_(OPEN_STATUSES)):
        if refresh(db, d, now):
            db.flush()
        if d.status in OPEN_STATUSES:
            return d
    return None


def create(db: Session, challenger: models.User, opponent_id: int, hsk_level: int | None,
           focus: str | None) -> models.Duel:
    if opponent_id == challenger.id:
        raise DuelError(400, "cannot_challenge_self")
    opponent = db.get(models.User, opponent_id)
    if opponent is None or not opponent.is_active or opponent.username.startswith("__"):
        raise DuelError(404, "opponent_not_found")
    if open_duel_between(db, challenger.id, opponent.id) is not None:
        raise DuelError(409, "duel_already_open")
    focus = focus if focus in FOCUS_TYPES else "mix"
    if hsk_level is None:
        # Fair default: the lower of the two players' current levels.
        hsk_level = min(user_rank(db, challenger)[0], user_rank(db, opponent)[0])
    if not 1 <= hsk_level <= 9:
        raise DuelError(422, "invalid_level")
    questions = build_questions(db, hsk_level, focus, seed=random.SystemRandom().randrange(2**31))
    if len(questions) < 4:
        raise DuelError(422, "not_enough_content")
    now = _now()
    duel = models.Duel(
        status="pending",
        challenge_type=focus,
        hsk_level=hsk_level,
        time_limit_seconds=TIME_LIMIT_SECONDS,
        question_data={"engine": ENGINE, "questions": questions},
        expires_at=now + CHALLENGE_TTL,
        created_at=now,
    )
    db.add(duel)
    db.flush()
    db.add(models.DuelParticipant(duel_id=duel.id, user_id=challenger.id, role="challenger"))
    db.add(models.DuelParticipant(duel_id=duel.id, user_id=opponent.id, role="opponent"))
    notifications.create_duel_notification(db, notifications.DUEL_CHALLENGE, challenger, opponent, duel.id)
    db.commit()
    db.refresh(duel)
    return duel


def _require_role(duel: models.Duel, user: models.User, role: str) -> models.DuelParticipant:
    me = side(duel, user.id)
    if me is None or me.role != role:
        raise DuelError(403, "not_allowed")
    return me


def accept(db: Session, duel: models.Duel, user: models.User) -> None:
    refresh(db, duel)
    _require_role(duel, user, "opponent")
    if duel.status != "pending":
        db.commit()
        raise DuelError(409, f"not_pending_{duel.status}")
    now = _now()
    duel.status = "active"
    duel.started_at = now
    duel.responded_at = now
    duel.play_deadline = now + PLAY_WINDOW
    challenger = other_side(duel, user.id)
    notifications.mark_duel_notifications_read(db, user.id, duel.id, notifications.DUEL_CHALLENGE)
    if challenger is not None:
        notifications.create_duel_notification(
            db, notifications.DUEL_ACCEPTED, user, db.get(models.User, challenger.user_id), duel.id
        )
    db.commit()


def decline(db: Session, duel: models.Duel, user: models.User) -> None:
    refresh(db, duel)
    _require_role(duel, user, "opponent")
    if duel.status != "pending":
        db.commit()
        raise DuelError(409, f"not_pending_{duel.status}")
    now = _now()
    duel.status = "declined"
    duel.responded_at = now
    duel.finished_at = now
    challenger = other_side(duel, user.id)
    notifications.mark_duel_notifications_read(db, user.id, duel.id, notifications.DUEL_CHALLENGE)
    if challenger is not None:
        notifications.create_duel_notification(
            db, notifications.DUEL_DECLINED, user, db.get(models.User, challenger.user_id), duel.id
        )
    db.commit()


def cancel(db: Session, duel: models.Duel, user: models.User) -> None:
    refresh(db, duel)
    _require_role(duel, user, "challenger")
    if duel.status != "pending":
        db.commit()
        raise DuelError(409, f"not_pending_{duel.status}")
    now = _now()
    duel.status = "cancelled"
    duel.responded_at = now
    duel.finished_at = now
    opp = other_side(duel, user.id)
    if opp is not None:
        # The challenge they were sent no longer exists.
        notifications.mark_duel_notifications_read(db, opp.user_id, duel.id, notifications.DUEL_CHALLENGE)
    db.commit()


def start_attempt(db: Session, duel: models.Duel, user: models.User) -> None:
    """Starts THIS player's clock. Idempotent: a refresh, a second tab or a
    reconnect never restarts it."""
    refresh(db, duel)
    if duel.status != "active":
        db.commit()
        raise DuelError(409, f"not_active_{duel.status}")
    me = side(duel, user.id)
    if me.finished:
        db.commit()
        return
    if me.started_at is None:
        me.started_at = _now()
    db.commit()


def answer(db: Session, duel: models.Duel, user: models.User, index: int, choice_id: int) -> dict:
    now = _now()
    refresh(db, duel, now)
    me = side(duel, user.id)
    if duel.status != "active":
        db.commit()
        raise DuelError(409, f"not_active_{duel.status}")
    if me.finished:
        db.commit()
        raise DuelError(409, "time_up" if me.finish_reason == "timeout" else "already_finished")
    if me.started_at is None:
        raise DuelError(409, "not_started")
    qs = _questions(duel)
    if not 0 <= index < len(qs):
        raise DuelError(422, "no_such_question")
    if index < (me.answered or 0):
        raise DuelError(409, "already_answered")
    if index != (me.answered or 0):
        # Questions are played in order; one answer per question per player.
        raise DuelError(409, "out_of_order")
    q = qs[index]
    if choice_id not in q["option_ids"]:
        raise DuelError(422, "invalid_option")
    end = deadline(duel, me)
    if now > end + ANSWER_GRACE:
        _finish(duel, me, "timeout", end)
        refresh(db, duel, now)
        db.commit()
        raise DuelError(409, "time_up")

    prev = max((a.answered_at for a in duel.answers if a.user_id == user.id), default=me.started_at)
    response_ms = max(0, int((min(now, end) - prev).total_seconds() * 1000))
    correct = choice_id == q["item_id"]
    points = POINTS_WRONG
    if correct:
        points = POINTS_CORRECT + round(max(0.0, 1 - response_ms / SPEED_BONUS_WINDOW_MS) * SPEED_BONUS_MAX)

    row = practice._row(db, q["item_type"], q["item_id"])
    db.add(models.DuelAnswer(
        duel_id=duel.id, user_id=user.id, question_index=index, choice_id=choice_id,
        correct=correct, points=points, response_ms=response_ms, answered_at=now,
    ))
    try:
        db.flush()
    except IntegrityError:
        # A concurrent submit for the same question (double click, 2nd tab) won.
        db.rollback()
        raise DuelError(409, "already_answered")
    me.answered = (me.answered or 0) + 1
    if correct:
        me.correct_count = (me.correct_count or 0) + 1
    me.score = (me.score or 0) + points
    if row is not None:
        # The duel answer is a real learning event: mastery/SRS, DNA,
        # mistakes, XP -- the same bookkeeping as a practice answer.
        practice._record(db, user, SimpleNamespace(source="duel"), q, row, correct, response_ms)
    if me.answered >= len(qs):
        _finish(duel, me, "completed", now)
    refresh(db, duel, now)
    db.commit()
    db.refresh(duel)
    # Right/wrong only: the correct option is revealed in the review once the
    # duel is completed, otherwise the first player to answer could pass the
    # answer key to the one still playing the same questions.
    return {"index": index, "correct": correct, "points": points, "response_ms": response_ms}


def forfeit(db: Session, duel: models.Duel, user: models.User) -> None:
    """Ends THIS player's attempt now (unanswered questions just don't
    score). Never touches the opponent's attempt."""
    now = _now()
    refresh(db, duel, now)
    me = side(duel, user.id)
    if duel.status != "active":
        db.commit()
        raise DuelError(409, f"not_active_{duel.status}")
    if not me.finished:
        _finish(duel, me, "forfeit", now)
        refresh(db, duel, now)
    db.commit()


# --------------------------------------------------------------------------- view

def _person(db: Session, user_id: int | None) -> dict:
    u = db.get(models.User, user_id) if user_id else None
    if u is None:
        return {"id": None, "username": None, "avatar_url": None, "animal_slug": None}
    return {
        "id": u.id,
        "username": u.username,
        "avatar_url": photo_url(u),
        "animal_slug": u.animal.slug if u.animal else None,
    }


def view(db: Session, duel: models.Duel, user: models.User, locale: str, with_questions: bool = True) -> dict:
    now = _now()
    me = side(duel, user.id)
    opp = other_side(duel, user.id)
    qs = _questions(duel)
    total = len(qs) if qs else max((me.answered or 0) if me else 0, (opp.answered or 0) if opp else 0)
    completed = duel.status == "completed"

    def player(p, own: bool) -> dict | None:
        if p is None:
            return None
        out = {
            **_person(db, p.user_id),
            "role": p.role,
            "started": p.started_at is not None,
            "finished": bool(p.finished),
            "finish_reason": p.finish_reason,
            "answered": p.answered or 0,
        }
        # The opponent's correctness and score stay private until the end.
        if own or completed:
            out.update({
                "correct": p.correct_count or 0,
                "score": p.score or 0,
                "time_used_ms": p.time_used_ms,
            })
        if own:
            out["remaining_ms"] = remaining_ms(duel, p, now) if duel.status == "active" else None
        return out

    result = None
    if completed:
        if duel.winner_id is None:
            outcome = "draw"
        else:
            outcome = "win" if duel.winner_id == user.id else "loss"
        result = {"outcome": outcome, "winner_id": duel.winner_id, "decided_by": duel.decided_by}

    data = {
        "id": duel.id,
        "status": duel.status,
        "legacy": is_legacy(duel),
        "focus": duel.challenge_type,
        "hsk_level": duel.hsk_level,
        "question_count": total,
        "time_limit_seconds": duel.time_limit_seconds or TIME_LIMIT_SECONDS,
        "created_at": duel.created_at,
        "expires_at": duel.expires_at,
        "accepted_at": duel.started_at if duel.responded_at and duel.status != "declined" else None,
        "play_deadline": duel.play_deadline,
        "finished_at": duel.finished_at,
        "server_now": now,
        "my_role": me.role if me else None,
        "can_accept": duel.status == "pending" and me is not None and me.role == "opponent",
        "can_decline": duel.status == "pending" and me is not None and me.role == "opponent",
        "can_cancel": duel.status == "pending" and me is not None and me.role == "challenger",
        "me": player(me, True),
        "opponent": player(opp, False),
        "result": result,
        "current": None,
        "review": None,
    }
    if with_questions and qs and me is not None:
        if completed:
            data["review"] = _render(db, duel, user.id, locale, reveal=True)
        elif duel.status == "active" and me.started_at is not None and not me.finished:
            idx = me.answered or 0
            if idx < len(qs):
                rendered = _render(db, duel, user.id, locale)
                data["current"] = rendered[idx]
    return data
