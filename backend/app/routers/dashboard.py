from datetime import datetime, time

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.routers.animals import _localize_animal
from app.routers.missions import _localize_mission
from app.routers.quests import _localize_quest
from app.services import achievements as achievements_svc
from app.services.avatars import photo_url
from app.services.dna import compute_dna
from app.services.gamification import (
    check_achievements,
    ensure_user_skills,
    generate_daily_quests,
    streak_snapshot,
    user_rank,
)
from app.services.localization import load_translations, tr
from app.services.practice import review_counts

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=schemas.DashboardResponse)
def dashboard(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    ensure_user_skills(db, user)
    if user.streak is None:
        # A transient (never-flushed) UserStreak() would leave every column
        # at Python's bare None instead of the model's default=, since
        # SQLAlchemy only applies Column(default=...) during an actual
        # INSERT. Persist it so the row — and its real defaults — exist.
        db.add(models.UserStreak(user_id=user.id))
    db.commit()
    db.refresh(user)

    check_achievements(db, user)
    ach_entries = achievements_svc.overview(db, user)
    dna = compute_dna(user)
    current, mastery = user_rank(db, user)

    quests = generate_daily_quests(db, user)

    next_mission = (
        db.query(models.Mission)
        .filter(models.Mission.min_hsk_level <= current)
        .order_by(models.Mission.sort_order)
        .first()
    )
    next_location = (
        db.query(models.Location)
        .filter(models.Location.unlock_level > current)
        .order_by(models.Location.unlock_level)
        .first()
    )
    if next_location is None:
        next_location = (
            db.query(models.Location).order_by(models.Location.unlock_level.desc()).first()
        )

    animal = None
    if user.animal_id:
        animal = db.get(models.Animal, user.animal_id)
    animal_tr = load_translations(db, "animal", [str(animal.id)] if animal else [], locale)

    skill_rows = {s.skill.code: s.skill for s in user.user_skills if s.skill}
    skill_tr = load_translations(db, "skill", [str(s.id) for s in skill_rows.values()], locale)

    def skill_name(code: str) -> str:
        row = skill_rows.get(code)
        return tr(skill_tr, row.id, "name", row.name) if row else code

    mission_tr = load_translations(db, "mission", [str(next_mission.id)] if next_mission else [], locale)
    location_tr = load_translations(db, "location", [str(next_location.id)] if next_location else [], locale)
    quest_tr = load_translations(db, "quest_template", [q.quest_type for q in quests], locale)

    next_location_out = None
    if next_location:
        next_location_out = schemas.LocationResponse.model_validate(next_location)
        next_location_out.name = tr(location_tr, next_location.id, "name", next_location_out.name)
        next_location_out.description = tr(location_tr, next_location.id, "description", next_location_out.description)

    earned = [e for e in ach_entries if e["link"] is not None]
    unseen = [e for e in earned if e["link"].notified_at is None]
    ach_out = achievements_svc.responses(db, earned + unseen + achievements_svc.closest(ach_entries), locale)
    n_earned, n_unseen = len(earned), len(unseen)

    due = review_counts(db, user)
    day_start = datetime.combine(datetime.utcnow().date(), time.min)
    minutes_today = (
        db.query(func.coalesce(func.sum(models.ActivityEvent.minutes), 0.0))
        .filter(models.ActivityEvent.user_id == user.id, models.ActivityEvent.created_at >= day_start)
        .scalar()
    )

    return schemas.DashboardResponse(
        user=user,
        avatar_url=photo_url(user),
        animal=_localize_animal(animal, animal_tr) if animal else None,
        hsk_level=current,
        mastery=mastery,
        dna=schemas.DNASummaryResponse(
            overall=dna["overall"],
            skills=[
                schemas.SkillMasteryResponse(
                    code=code,
                    name=skill_name(code),
                    mastery=value,
                    xp=next((s.xp for s in user.user_skills if s.skill and s.skill.code == code), 0),
                    status="strong" if value >= 70 else ("developing" if value >= 40 else "weak"),
                )
                for code, value in dna["skills"].items()
            ],
            # A skill nobody has practised yet is untested, not weak: a new learner
            # used to see all nine listed under "needs work" (the assistant
            # already applied this rule).
            weak_areas=[skill_name(s.skill.code) for s in user.user_skills if s.skill and s.mastery <= 30]
            if any(s.mastery > 0 for s in user.user_skills) else [],
            strong_areas=[skill_name(s.skill.code) for s in user.user_skills if s.skill and s.mastery >= 70],
        ),
        streak=schemas.StreakResponse(**streak_snapshot(user.streak)),
        daily_goal={
            "daily_goal_minutes": user.profile.daily_goal_minutes if user.profile else 10,
            # Today's logged learning activity (same per-action weights the
            # Progress page uses), not the all-time voice total it used to sum.
            "minutes_today": round(minutes_today),
        },
        recommended_mission=_localize_mission(next_mission, mission_tr) if next_mission else None,
        recent_mistakes=(
            db.query(models.LearningMistake)
            .filter(
                models.LearningMistake.user_id == user.id,
                models.LearningMistake.mastered.is_(False),
            )
            .order_by(models.LearningMistake.priority.desc())
            .limit(5)
            .all()
        ),
        next_location=next_location_out,
        quests_today=[_localize_quest(q, quest_tr) for q in quests],
        achievements=ach_out[:n_earned],
        new_achievements=ach_out[n_earned:n_earned + n_unseen],
        next_achievements=ach_out[n_earned + n_unseen:],
        review_due=due["total"] + due["mistakes"],
    )