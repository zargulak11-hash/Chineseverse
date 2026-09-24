from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud import apply_updates, get_or_404
from app.database import get_db
from app.deps import get_locale
from app.services.localization import load_translations, tr

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


def _localize(lesson: models.Lesson, translations: dict) -> schemas.LessonResponse:
    out = schemas.LessonResponse.model_validate(lesson)
    key = str(lesson.id)
    out.title = tr(translations, key, "title", out.title)
    out.summary = tr(translations, key, "summary", out.summary)
    out.content = tr(translations, key, "content", out.content)
    return out


def _level(db: Session, hsk_level: int) -> models.HSKLevel:
    level = db.query(models.HSKLevel).filter(models.HSKLevel.level == hsk_level).first()
    if level is None:
        raise HTTPException(status_code=404, detail=f"HSK level {hsk_level} not found")
    return level


@router.get("", response_model=list[schemas.LessonResponse])
def list_lessons(
    hsk_level: int | None = None,
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    query = db.query(models.Lesson).join(models.HSKLevel, models.Lesson.hsk_level_id == models.HSKLevel.id)
    if hsk_level is not None:
        query = query.filter(models.HSKLevel.level == hsk_level)
    lessons = query.order_by(models.HSKLevel.level, models.Lesson.order_index).all()
    translations = load_translations(db, "lesson", [str(l.id) for l in lessons], locale)
    return [_localize(l, translations) for l in lessons]


@router.post("", response_model=schemas.LessonResponse, status_code=201)
def create_lesson(payload: schemas.LessonCreate, db: Session = Depends(get_db)):
    level = _level(db, payload.hsk_level)
    lesson = models.Lesson(
        hsk_level_id=level.id,
        title=payload.title,
        summary=payload.summary if hasattr(payload, "summary") else None,
        content=payload.content,
        lesson_type=payload.lesson_type,
        order_index=payload.order_index,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.get("/{lesson_id}", response_model=schemas.LessonResponse)
def get_lesson(lesson_id: int, db: Session = Depends(get_db), locale: str = Depends(get_locale)):
    lesson = get_or_404(db, models.Lesson, lesson_id)
    translations = load_translations(db, "lesson", [str(lesson_id)], locale)
    return _localize(lesson, translations)


@router.put("/{lesson_id}", response_model=schemas.LessonResponse)
def update_lesson(
    lesson_id: int, payload: schemas.LessonUpdate, db: Session = Depends(get_db)
):
    lesson = get_or_404(db, models.Lesson, lesson_id)
    level = _level(db, payload.hsk_level)
    lesson.hsk_level_id = level.id
    lesson.title = payload.title
    lesson.content = payload.content
    lesson.lesson_type = payload.lesson_type
    lesson.order_index = payload.order_index
    db.commit()
    db.refresh(lesson)
    return lesson


@router.patch("/{lesson_id}", response_model=schemas.LessonResponse)
def patch_lesson(
    lesson_id: int, payload: schemas.LessonPatch, db: Session = Depends(get_db)
):
    lesson = get_or_404(db, models.Lesson, lesson_id)
    data = payload.model_dump(exclude_unset=True)
    if "hsk_level" in data:
        level = _level(db, data.pop("hsk_level"))
        data["hsk_level_id"] = level.id
    apply_updates(lesson, data)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.delete("/{lesson_id}", status_code=204)
def delete_lesson(lesson_id: int, db: Session = Depends(get_db)):
    lesson = get_or_404(db, models.Lesson, lesson_id)
    db.delete(lesson)
    db.commit()