"""Gamification glue: user skill rows, daily quests, achievement checks,
and small progression helpers shared between routers."""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models

QUEST_TEMPLATES = [
    ("speaking", "Say it out loud", "Complete 3 voice turns in conversations.",
     3, 30, 5, "Your companion is listening. Speak!"),
    ("vocab", "Word harvest", "Review or master 5 vocabulary cards.",
     5, 30, 5, "Fresh words are ready to pick."),
    ("lesson", "Lesson focus", "Complete 1 lesson.",
     1, 40, 5, "Steady lessons build the bridge."),
    ("case", "Detective hour", "Solve or attempt 1 case.",
     1, 50, 10, "A little mystery sharpens the mind."),
    ("listening", "Ears first", "Replay 3 NPC lines in the world.",
     3, 25, 5, "Listen once more — tones are everywhere."),
    ("duel", "Friendly duel", "Finish 1 duel.",
     1, 45, 10, "A duel wakes up your reaction speed."),
]

# Each animal's preferred quest_type(s) / Mission.kind(s) / duel focus_type,
# read directly off its seeded `preferred_mechanics` text (see seed.py's
# ANIMALS list) rather than invented lore. quest_type and mission "kind" use
# slightly different vocabularies in the schema (quests: speaking/vocab/
# lesson/case/listening/duel; missions: speak/listen/vocab/case/world/duel)
# so each animal maps to both. An animal with no strong signal in its own
# text (panda: "Balanced practice") intentionally gets an empty/neutral
# entry rather than a forced bias. `duel_focus` must be a key `duels.py`
# already recognizes as a real DuelQuestion type (see VALID_FOCUS_TYPES).
#
# Mission.kind's real seeded vocabulary is {speak, listening, conversation,
# case, vocab, duel, teach} — the model's inline comment (speak|listen|
# vocab|case|world|duel) is stale, so this table uses the values actually
# in the data, confirmed against the live DB, not the comment.
ANIMAL_BIAS: dict[str, dict] = {
    "bird":         {"quests": ["speaking"],         "mission_kinds": ["speak"],              "duel_focus": "tone"},
    "capybara":     {"quests": ["lesson"],            "mission_kinds": ["conversation"],       "duel_focus": None},
    "panther":      {"quests": ["case"],              "mission_kinds": ["case"],               "duel_focus": "translate"},
    "sheep":        {"quests": ["vocab"],             "mission_kinds": ["vocab"],              "duel_focus": "meaning"},
    "fox":          {"quests": ["vocab", "duel"],     "mission_kinds": ["vocab", "duel"],      "duel_focus": "reaction"},
    "wolf":         {"quests": ["duel"],              "mission_kinds": ["duel", "conversation"], "duel_focus": "character"},
    "snake":        {"quests": ["vocab"],             "mission_kinds": ["vocab"],              "duel_focus": "memory"},
    "cat":          {"quests": ["listening"],         "mission_kinds": ["listening"],          "duel_focus": "listening"},
    "dog":          {"quests": ["vocab", "lesson"],   "mission_kinds": ["vocab"],              "duel_focus": "meaning"},
    "tiger":        {"quests": ["duel", "case"],      "mission_kinds": ["duel", "case"],       "duel_focus": "translate"},
    "rabbit":       {"quests": ["vocab"],             "mission_kinds": ["vocab"],              "duel_focus": "pinyin"},
    "panda":        {"quests": [],                    "mission_kinds": [],                     "duel_focus": None},
    "red-panda":    {"quests": ["vocab"],             "mission_kinds": ["vocab"],              "duel_focus": "meaning"},
    "phoenix":      {"quests": ["vocab"],             "mission_kinds": ["case"],               "duel_focus": "character"},
    "monkey":       {"quests": ["duel", "speaking"],  "mission_kinds": ["duel", "conversation"], "duel_focus": "reaction"},
    "koala":        {"quests": ["listening"],         "mission_kinds": ["listening"],          "duel_focus": "listening"},
    "elephant":     {"quests": ["vocab"],             "mission_kinds": ["vocab"],              "duel_focus": "memory"},
    "cow":          {"quests": ["lesson"],            "mission_kinds": ["teach"],              "duel_focus": "translate"},
    "penguin":      {"quests": ["speaking"],          "mission_kinds": ["conversation", "speak"], "duel_focus": "meaning"},
    "owl":          {"quests": ["case", "lesson"],    "mission_kinds": ["case", "teach"],      "duel_focus": "recognition"},
}

_NEUTRAL_BIAS = {"quests": [], "mission_kinds": [], "duel_focus": None}

# How much more likely a preferred quest_type is to be picked for the daily
# trio, relative to a non-preferred one (weight, not a guarantee — the daily
# quests should still feel varied, not monoculture).
PREFERRED_QUEST_WEIGHT = 4


def animal_bias(user: models.User) -> dict:
    """This user's animal-driven content bias, or a neutral no-op bias if
    they haven't chosen a companion yet."""
    animal = user.animal
    if animal is None or animal.slug not in ANIMAL_BIAS:
        return _NEUTRAL_BIAS
    return ANIMAL_BIAS[animal.slug]


def _pick_quest_templates(preferred_types: list[str], k: int = 3) -> list[tuple]:
    """Weighted sample of QUEST_TEMPLATES, without replacement, biased
    toward `preferred_types`. Pure function (no DB) so it's directly
    testable for distribution."""
    pool = list(QUEST_TEMPLATES)
    weights = [PREFERRED_QUEST_WEIGHT if t[0] in preferred_types else 1 for t in pool]
    chosen = []
    for _ in range(min(k, len(pool))):
        picked = random.choices(pool, weights=weights, k=1)[0]
        idx = pool.index(picked)
        chosen.append(pool.pop(idx))
        weights.pop(idx)
    return chosen


def valid_timezone(name: str | None) -> str | None:
    """`name` when it is a real IANA zone ("Asia/Dushanbe"), else None. It
    comes from a request header, so anything ZoneInfo refuses (unknown
    names, paths, junk) is simply not used."""
    if not name or len(name) > 64:
        return None
    try:
        ZoneInfo(name)
    except Exception:  # ZoneInfoNotFoundError, ValueError on malformed keys, ...
        return None
    return name


def learner_tz(user: models.User | None) -> tzinfo:
    """The learner's own time zone; UTC until the app has seen it."""
    name = valid_timezone(getattr(user, "timezone", None))
    return ZoneInfo(name) if name else timezone.utc


def local_date(user: models.User | None, at: datetime) -> date:
    """The learner's calendar day of `at`, a naive UTC timestamp as every
    created_at column stores it (datetime.utcnow())."""
    return at.replace(tzinfo=timezone.utc).astimezone(learner_tz(user)).date()


def local_day_start(user: models.User | None, day: date) -> datetime:
    """Midnight of the learner's `day`, as the naive UTC timestamp to
    compare created_at columns against."""
    start = datetime.combine(day, time.min, tzinfo=learner_tz(user))
    return start.astimezone(timezone.utc).replace(tzinfo=None)


def activity_today(user: models.User | None = None) -> date:
    """The calendar day activity counts toward: the learner's own date.

    It used to be the UTC date for everyone, so for a learner in Dushanbe
    (UTC+5) everything between midnight and 05:00 landed on the previous
    day -- studying on four consecutive evenings and nights read as a broken
    streak. Without a known zone (or a user) this is still the UTC date,
    never date.today(), the server's own local date."""
    return local_date(user, datetime.utcnow())


def learning_days(db: Session, user: models.User) -> set[date]:
    """Every day the learner did something that logged an ActivityEvent --
    the real learning actions (services/activity.py), never page views --
    in their own calendar."""
    rows = db.query(models.ActivityEvent.created_at).filter(models.ActivityEvent.user_id == user.id)
    return {local_date(user, at) for (at,) in rows if at is not None}


def _run_ending(days: set[date], last: date) -> int:
    """Consecutive days in `days` ending on `last`."""
    n = 0
    while last - timedelta(days=n) in days:
        n += 1
    return n


def _longest_run(days: set[date]) -> int:
    # Every run is measured once, from its last day.
    return max((_run_ending(days, d) for d in days if d + timedelta(days=1) not in days), default=0)


def sync_streak(db: Session, user: models.User, at: datetime) -> bool:
    """Bring user.streak up to date with the activity log after a learning
    action at `at` (naive UTC) was added. Returns True when that action was
    the first of its day, i.e. the day just started counting.

    The streak row used to be a counter bumped in place by touch_streak:
    days were UTC days, choosing a companion or a bare "ping" counted as a
    learning day, and a day it got wrong stayed wrong forever. Now the log
    is the record: once per learning day the run is recomputed from it in
    the learner's own calendar. Stored history is never lowered --
    longest/total keep whatever they held before (days from before the log
    existed), and a run still going on from before the log began is kept."""
    db.flush()  # the new event (autoflush is off)
    day = local_date(user, at)
    row = user.streak
    if row is None:
        # Attached through the relationship, in the caller's own session, so
        # a second action in this request sees it (user_id is unique). The
        # caller commits.
        row = user.streak = models.UserStreak(
            user_id=user.id, current_streak=0, longest_streak=0, total_active_days=0,
        )
    start = local_day_start(user, day)
    same_day = (
        db.query(models.ActivityEvent.id)
        .filter(
            models.ActivityEvent.user_id == user.id,
            models.ActivityEvent.created_at >= start,
            models.ActivityEvent.created_at < local_day_start(user, day + timedelta(days=1)),
        )
        .limit(2)
        .count()
    )
    new_day = same_day <= 1
    if not new_day and row.last_active_date == day:
        return False  # already counted today: nothing changes until tomorrow

    days = learning_days(db, user)
    last = max(days)
    current = _run_ending(days, last)
    stored_alive = row.last_active_date is not None and row.last_active_date >= last - timedelta(days=current)
    if current and last - timedelta(days=current - 1) == min(days) and stored_alive:
        # The run reaches back to the first logged action: it may have begun
        # before the activity log existed, which only the old counter knows.
        current = max(current, row.current_streak or 0)
    row.current_streak = current
    row.longest_streak = max(row.longest_streak or 0, _longest_run(days), current)
    row.total_active_days = max((row.total_active_days or 0) + (1 if new_day else 0), len(days))
    row.last_active_date = last
    return new_day


def streak_snapshot(user: models.User) -> dict:
    """The streak as of the learner's today, for display (StreakResponse).
    The stored run only changes on the next learning action, so after missed
    days it still held the old run; a streak whose last learning day is
    before the learner's yesterday is already broken. Read-only -- nothing
    is written, longest/total are reported as stored."""
    streak = user.streak
    today = activity_today(user)
    current = 0
    if streak is not None and streak.last_active_date and streak.last_active_date >= today - timedelta(days=1):
        current = streak.current_streak or 0
    return {
        "current_streak": current,
        "longest_streak": (streak.longest_streak if streak else 0) or 0,
        "total_active_days": (streak.total_active_days if streak else 0) or 0,
        "last_active_date": streak.last_active_date if streak else None,
    }


def ensure_user_skills(db: Session, user: models.User) -> None:
    if user.user_skills:
        return
    # Anything else already pending in this request; only a clean session may
    # safely roll back below.
    pending = bool(db.new or db.dirty or db.deleted)
    for skill in db.query(models.Skill).all():
        db.add(models.UserSkill(user_id=user.id, skill_id=skill.id, level=1, xp=0, mastery=0.0))
    try:
        db.commit()
    except IntegrityError:
        # A new account's first page load sends GET /dashboard and the page's
        # own request at once; both found no skill rows and both inserted
        # them, so the loser hit uq(user_id, skill_id) and the learner's very
        # first screen showed a server error. The winner's rows are the same
        # rows, so the loser just uses them.
        db.rollback()
        if pending:
            raise
        db.refresh(user)


# (ensure_bond used to live here: GET /api/dashboard, a location's detail
# and Pet Teacher silently made the panda the learner's main companion when
# none was chosen yet. Since every page loads the dashboard, a new learner
# already had a panda "picked" on the very screen that asks them to choose.
# The main companion is now only ever the learner's own choice (POST
# /api/me/animal); bond points simply wait until one exists.)


def generate_daily_quests(db: Session, user: models.User, force: bool = False) -> list[models.DailyQuest]:
    today = date.today()
    existing = (
        db.query(models.DailyQuest)
        .filter(models.DailyQuest.user_id == user.id, models.DailyQuest.quest_date == today)
        .all()
    )
    if existing and not force:
        return existing

    if not existing:
        chosen = _pick_quest_templates(animal_bias(user)["quests"], k=3)
        for qtype, title, desc, target, xp, coins, flavor in chosen:
            db.add(
                models.DailyQuest(
                    user_id=user.id, quest_date=today, quest_type=qtype,
                    title=title, description=desc, target=target,
                    reward_xp=xp, reward_coins=coins, flavor=flavor,
                )
            )
        db.commit()
        existing = (
            db.query(models.DailyQuest)
            .filter(models.DailyQuest.user_id == user.id, models.DailyQuest.quest_date == today)
            .all()
        )
    return existing


def progress_quests(db: Session, user: models.User, quest_type: str, amount: int = 1) -> list[models.DailyQuest]:
    today = date.today()
    quests = (
        db.query(models.DailyQuest)
        .filter(
            models.DailyQuest.user_id == user.id,
            models.DailyQuest.quest_date == today,
            models.DailyQuest.quest_type == quest_type,
            models.DailyQuest.completed.is_(False),
        )
        .all()
    )
    for q in quests:
        q.progress = min(q.target, q.progress + amount)
        if q.progress >= q.target:
            q.completed = True
    return quests


def progress_missions(
    db: Session, user: models.User, kind: str, scenario_id: int | None = None, amount: int = 1
) -> list[models.Mission]:
    """Auto-advance any mission of this kind the learner is eligible for.

    A mission tied to a specific scenario (scenario_id is not None) only
    advances when that exact scenario was just used; a kind-only mission
    (e.g. the generic "listening" drill) advances on any qualifying action.
    Rewards are granted immediately the moment a mission completes — no
    separate claim step, unlike daily quests.
    """
    missions = db.query(models.Mission).filter(models.Mission.kind == kind).all()
    completed_now = []
    level = None
    for mission in missions:
        if mission.scenario_id is not None and mission.scenario_id != scenario_id:
            continue
        # A mission above the learner's HSK level is locked (routers/missions.py).
        if (mission.min_hsk_level or 1) > 1:
            if level is None:
                level = user_rank(db, user)[0]
            if mission.min_hsk_level > level:
                continue
        entry = (
            db.query(models.UserMission)
            .filter_by(user_id=user.id, mission_id=mission.id)
            .first()
        )
        if entry is None:
            entry = models.UserMission(user_id=user.id, mission_id=mission.id, status="active", progress=0)
            db.add(entry)
            db.flush()
        if entry.status == "completed":
            continue
        entry.status = "active"
        entry.progress = min(mission.target_count, entry.progress + amount)
        if entry.progress >= mission.target_count:
            entry.status = "completed"
            entry.completed_at = datetime.utcnow()
            user.total_xp += mission.reward_xp
            user.coins += mission.reward_coins
            add_bond_points(user, points=3)
            completed_now.append(mission)
    return completed_now


def check_achievements(db: Session, user: models.User) -> list[models.Achievement]:
    """Unlock what the learner's records now earn (services/achievements.py
    owns the rules). Kept here because every learning router calls it."""
    from app.services import achievements

    return achievements.check(db, user)


def add_bond_points(user: models.User, points: int = 1) -> None:
    if user.user_animal:
        user.user_animal.bond_points += points
        user.user_animal.interactions += 1
        level = user.user_animal.bond_level
        if user.user_animal.bond_points >= level * 20:
            user.user_animal.bond_level = min(5, level + 1)


# Spaced-repetition base intervals, keyed by how urgent the item still is
# (LearningMistake.priority, 0-5: 0 = mastered, 5 = repeatedly missed).
# A fresh failure always resets to the shortest cycle; a success schedules
# the NEXT review further out the lower the remaining priority is — a
# simple exponential-backoff-on-success / reset-on-failure scheme.
_FAILURE_INTERVAL = timedelta(hours=6)
_SUCCESS_INTERVAL_BY_PRIORITY = {
    5: timedelta(hours=12), 4: timedelta(days=1), 3: timedelta(days=2),
    2: timedelta(days=4), 1: timedelta(days=8), 0: timedelta(days=16),
}


def memory_multiplier(user: models.User) -> float:
    """Snake's seeded special_ability is literally 'Memory Coil:
    spaced-repetition intervals improve 2x' — the one animal bonus with an
    unambiguous, already-written mechanical meaning, so it's wired in here
    rather than left as unread flavor text."""
    animal = user.animal
    return 2.0 if animal and animal.slug == "snake" else 1.0


def record_mistake(
    db: Session,
    user: models.User,
    mistake_type: str,
    reference: str,
    *,
    question_text: str | None = None,
    answer_given: str | None = None,
    correct_answer: str | None = None,
) -> models.LearningMistake:
    """Log or reinforce a recurring learner mistake so the world can bring it back later."""
    reference = (reference or "").strip()[:300] or "unspecified"
    row = (
        db.query(models.LearningMistake)
        .filter_by(user_id=user.id, mistake_type=mistake_type, reference=reference)
        .first()
    )
    now = datetime.utcnow()
    if row is None:
        row = models.LearningMistake(
            user_id=user.id,
            mistake_type=mistake_type,
            reference=reference,
            question_text=question_text,
            answer_given=answer_given,
            correct_answer=correct_answer,
            priority=1,
            occurrences=1,
            mastered=False,
            last_seen_at=now,
            next_review_at=now + _FAILURE_INTERVAL,
        )
        db.add(row)
    else:
        row.occurrences += 1
        row.priority = min(5, row.priority + 1)
        row.mastered = False
        row.mastered_at = None
        row.question_text = question_text or row.question_text
        row.answer_given = answer_given or row.answer_given
        row.correct_answer = correct_answer or row.correct_answer
        row.last_seen_at = now
        row.next_review_at = now + _FAILURE_INTERVAL
    return row


def reinforce_mistake(db: Session, user: models.User, mistake_type: str, reference: str) -> None:
    """Called when the learner gets it right — cools the mistake down toward
    mastery and pushes its next review further out (spaced repetition)."""
    reference = (reference or "").strip()[:300] or "unspecified"
    row = (
        db.query(models.LearningMistake)
        .filter_by(user_id=user.id, mistake_type=mistake_type, reference=reference)
        .first()
    )
    if row is None or row.mastered:
        return
    row.priority = max(0, row.priority - 1)
    now = datetime.utcnow()
    row.last_seen_at = now
    if row.priority == 0:
        row.mastered = True
        row.mastered_at = now
        row.next_review_at = None
    else:
        base = _SUCCESS_INTERVAL_BY_PRIORITY[row.priority]
        row.next_review_at = now + base * memory_multiplier(user)


def user_rank(db: Session, user: models.User) -> tuple[int, float]:
    """(current HSK level, overall mastery 0-100)."""
    ensure_user_skills(db, user)
    skills = [s for s in user.user_skills if s.skill]
    if not skills:
        return 1, 0.0
    overall = sum(s.mastery for s in skills) / len(skills)
    levels = sorted({hsk.level for hsk in db.query(models.HSKLevel).all()})
    current = 1
    for level in levels:
        if overall >= max(0, (level - 1) * 15):
            current = max(current, level)
    # Never below where the learner really is on the lesson path: finishing
    # every HSK 1 lesson opens HSK 2 there, and the dashboard, Roadmap and
    # World must agree instead of still showing HSK 1 until the DNA average
    # catches up. Only raises the level; the DNA rank (and the placement
    # test that writes it) still counts. Capped at the highest HSKLevel row
    # (the shared 7-9 band is level 7 here; the Roadmap refines the stage).
    # Imported here: lesson_path builds on practice, which imports this module.
    from app.services.lesson_path import path_level

    if levels:
        current = max(current, min(path_level(db, user), levels[-1]))
    return current, round(overall, 1)


def location_status(location: models.Location, current_level: int) -> str:
    """Same unlock rule World's map uses, exposed here so any router that
    needs to gate access to a location's content (not just display a badge)
    can check it without importing another router."""
    if location.unlock_level <= current_level:
        return "unlocked"
    if location.unlock_level == current_level + 1:
        return "next"
    return "locked"


def scenario_is_unlocked(db: Session, user: models.User | None, scenario: models.Scenario) -> bool:
    location = db.get(models.Location, scenario.location_id)
    if location is None:
        return True
    current = user_rank(db, user)[0] if user else 1
    return location_status(location, current) == "unlocked"