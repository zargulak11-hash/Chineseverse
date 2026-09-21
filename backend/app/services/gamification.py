"""Gamification glue: user skill rows, daily quests, achievement checks,
and small progression helpers shared between routers."""

from __future__ import annotations

from datetime import date, timedelta

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


def touch_streak(user: models.User) -> bool:
    """Returns True when a new day just started (streak was bumped)."""
    streak = user.streak
    today = date.today()
    if streak is None:
        from app.database import SessionLocal

        with SessionLocal() as session:
            session.add(models.UserStreak(user_id=user.id, last_active_date=today, current_streak=1, total_active_days=1))
            session.commit()
        return True
    if streak.last_active_date == today:
        return False
    if streak.last_active_date == today - timedelta(days=1):
        streak.current_streak += 1
    else:
        streak.current_streak = 1
    streak.longest_streak = max(streak.longest_streak, streak.current_streak)
    streak.total_active_days += 1
    streak.last_active_date = today
    return True


def ensure_user_skills(db: Session, user: models.User) -> None:
    if user.user_skills:
        return
    for skill in db.query(models.Skill).all():
        db.add(models.UserSkill(user_id=user.id, skill_id=skill.id, level=1, xp=0, mastery=0.0))
    db.commit()


def ensure_bond(db: Session, user: models.User) -> None:
    """Attach the default animal if none chosen."""
    if user.user_animal is None and user.animal_id is None:
        panda = db.query(models.Animal).filter_by(slug="panda").first()
        if panda:
            user.animal_id = panda.id
            db.add(models.UserAnimal(user_id=user.id, animal_id=panda.id, bond_level=1))
            db.commit()


def generate_daily_quests(db: Session, user: models.User, force: bool = False) -> list[models.DailyQuest]:
    today = date.today()
    existing = (
        db.query(models.DailyQuest)
        .filter(models.DailyQuest.user_id == user.id, models.DailyQuest.quest_date == today)
        .all()
    )
    if existing and not force:
        return existing

    import random
    if not existing:
        chosen = random.sample(QUEST_TEMPLATES, k=3)
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


def _count(db: Session, user: models.User, criteria: dict):
    ctype = criteria.get("type")
    target = criteria.get("target")
    if ctype == "voice_count":
        return len(user.voice_attempts)
    if ctype == "avg_tones":
        attempts = list(user.voice_attempts)
        if not attempts:
            return 0
        return sum(a.tones or 0 for a in attempts) / len(attempts)
    if ctype == "scenario":
        scenario = db.query(models.Scenario).filter_by(slug=target).first()
        target_id = scenario.id if scenario else -1
        return sum(1 for a in user.voice_attempts if a.scenario_id == target_id)
    if ctype == "case_count":
        scenario_ids = {
            s.id for s in db.query(models.Scenario).filter(models.Scenario.is_case.is_(True)).all()
        }
        return sum(1 for a in user.voice_attempts if a.scenario_id in scenario_ids)
    if ctype == "streak":
        return (user.streak.current_streak if user.streak else 0)
    if ctype == "hsk":
        mastery = next(
            (s.mastery for s in user.user_skills if s.skill and s.skill.code == "vocabulary"), 0
        )
        return mastery
    if ctype == "duel_wins":
        return sum(1 for p in user.participants if p.score and p.score > 0)
    if ctype == "vocab_mastered":
        return len([w for w in user.user_vocabulary if w.status == "mastered"])
    if ctype == "bond_level":
        return user.user_animal.bond_level if user.user_animal else 0
    if ctype == "mistakes_mastered":
        return len([m for m in user.learning_mistakes if m.mastered])
    if ctype == "locations_unlocked":
        return 1
    if ctype == "mission_count":
        return len([m for m in user.user_missions if m.status in ("completed", "active")])
    return 0


def check_achievements(db: Session, user: models.User) -> list[models.Achievement]:
    unlocked = [ua.achievement for ua in user.user_achievements]
    unlocked_codes = {a.code for a in unlocked}
    newly = []
    for ach in db.query(models.Achievement).all():
        if ach.code in unlocked_codes or not ach.criteria:
            continue
        target = ach.criteria.get("target", 1)
        value = _count(db, user, ach.criteria)
        if isinstance(target, str):
            # Target is a slug/label; _count already filtered for it.
            achieved = value >= 1
        else:
            achieved = value >= int(target)
        if achieved:
            db.add(models.UserAchievement(user_id=user.id, achievement_id=ach.id))
            newly.append(ach)
    if newly:
        db.commit()
    return newly


def add_bond_points(user: models.User, points: int = 1) -> None:
    if user.user_animal:
        user.user_animal.bond_points += points
        user.user_animal.interactions += 1
        level = user.user_animal.bond_level
        if user.user_animal.bond_points >= level * 20:
            user.user_animal.bond_level = min(5, level + 1)


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
    return current, round(overall, 1)