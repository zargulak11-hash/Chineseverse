from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services.dna import compute_dna
from app.services.gamification import (
    check_achievements,
    ensure_bond,
    ensure_user_skills,
    generate_daily_quests,
    user_rank,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=schemas.DashboardResponse)
def dashboard(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_user_skills(db, user)
    ensure_bond(db, user)
    db.commit()
    db.refresh(user)

    check_achievements(db, user)
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

    return schemas.DashboardResponse(
        user=user,
        animal=schemas.AnimalResponse.model_validate(animal) if animal else None,
        hsk_level=current,
        mastery=mastery,
        dna=schemas.DNASummaryResponse(
            overall=dna["overall"],
            skills=[
                schemas.SkillMasteryResponse(
                    code=code,
                    name=next(
                        (s.skill.name for s in user.user_skills if s.skill and s.skill.code == code), code
                    ),
                    mastery=value,
                    xp=next((s.xp for s in user.user_skills if s.skill and s.skill.code == code), 0),
                    status="strong" if value >= 70 else ("developing" if value >= 40 else "weak"),
                )
                for code, value in dna["skills"].items()
            ],
            weak_areas=dna["weaknesses"],
            strong_areas=dna["strengths"],
        ),
        streak=user.streak or models.UserStreak(user_id=user.id),
        daily_goal={
            "daily_goal_minutes": user.profile.daily_goal_minutes if user.profile else 10,
            "minutes_today": min(
                sum(a.response_time_ms for a in user.voice_attempts) // 60000,
                60 * 6,
            ),
        },
        recommended_mission=next_mission,
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
        next_location=schemas.LocationResponse.model_validate(next_location) if next_location else None,
        quests_today=[schemas.QuestResponse.model_validate(q) for q in quests],
        achievements=[
            schemas.AchievementResponse.model_validate(ua.achievement)
            for ua in user.user_achievements
        ],
    )