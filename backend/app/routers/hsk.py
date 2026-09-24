from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services.gamification import ensure_user_skills, user_rank
from app.services.localization import load_translations, tr

router = APIRouter(prefix="/api/hsk", tags=["hsk"])


@router.get("/levels", response_model=list[schemas.HSKLevelResponse])
def list_levels(db: Session = Depends(get_db), locale: str = Depends(get_locale)):
    levels = db.query(models.HSKLevel).order_by(models.HSKLevel.level).all()
    translations = load_translations(db, "hsk_level", [str(l.id) for l in levels], locale)
    out = []
    for lvl in levels:
        item = schemas.HSKLevelResponse.model_validate(lvl)
        item.title = tr(translations, lvl.id, "title", item.title)
        item.description = tr(translations, lvl.id, "description", item.description)
        out.append(item)
    return out


@router.get("/skills", response_model=list[schemas.SkillResponse])
def list_skills(db: Session = Depends(get_db), locale: str = Depends(get_locale)):
    skills = db.query(models.Skill).order_by(models.Skill.id).all()
    translations = load_translations(db, "skill", [str(s.id) for s in skills], locale)
    out = []
    for skill in skills:
        item = schemas.SkillResponse.model_validate(skill)
        item.name = tr(translations, skill.id, "name", item.name)
        item.description = tr(translations, skill.id, "description", item.description)
        out.append(item)
    return out


@router.get("/roadmap", response_model=schemas.HSKRoadmapResponse)
def roadmap(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_user_skills(db, user)
    levels = db.query(models.HSKLevel).order_by(models.HSKLevel.level).all()
    current_level, overall = user_rank(db, user)

    results = []
    for lvl in levels:
        total = (
            db.query(models.VocabularyWord)
            .filter(models.VocabularyWord.hsk_level_id == lvl.id)
            .count()
        )
        mastered_ids = {
            w.word_id for w in user.user_vocabulary if w.status == "mastered"
        }
        mastered = (
            db.query(models.VocabularyWord)
            .filter(
                models.VocabularyWord.hsk_level_id == lvl.id,
                models.VocabularyWord.id.in_(list(mastered_ids) or [0]),
            )
            .count()
        )
        completed = (
            db.query(models.Progress)
            .join(models.Lesson, models.Progress.lesson_id == models.Lesson.id)
            .join(models.HSKLevel, models.Lesson.hsk_level_id == models.HSKLevel.id)
            .filter(
                models.Progress.user_id == user.id,
                models.Progress.status == "completed",
                models.HSKLevel.id == lvl.id,
            )
            .count()
        )
        total_lessons = (
            db.query(models.Lesson).filter(models.Lesson.hsk_level_id == lvl.id).count()
        )
        mastery = (mastered / total * 100.0) if total else 0.0
        if lvl.level < current_level:
            status = "unlocked"
        elif lvl.level == current_level:
            status = "current"
        else:
            status = "locked"
        ready = mastery >= lvl.mastery_to_unlock_next or lvl.level < current_level
        results.append(
            schemas.HSKLevelProgress(
                level=lvl.level, status=status,
                vocab_mastered=mastered, vocab_total=total,
                mastery=round(mastery, 1), lessons_completed=completed,
                ready_for_next=ready,
            )
        )
    return schemas.HSKRoadmapResponse(
        levels=results, current_level=current_level, overall_mastery=overall
    )