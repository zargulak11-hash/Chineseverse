from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud import apply_updates, get_or_404
from app.database import get_db
from app.deps import get_current_user, get_locale, get_user_or_none, require_admin
from app.services import lesson_path
from app.services.hsk_band import display_level_for_row, resolve_level_filter
from app.services.localization import load_translations, tr
from app.services.practice import lesson_body, lesson_items

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


def _localize(db: Session, lesson: models.Lesson, translations: dict) -> schemas.LessonResponse:
    out = schemas.LessonResponse.model_validate(lesson)
    # A lesson whose level is the shared HSK 7-9 band reports the real third
    # (7/8/9) it belongs to, not always the band's literal level=7 -- so
    # /lessons (unfiltered) groups it under the correct stage heading, the
    # same stage the level-filtered vocab/hanzi/grammar/roadmap views use.
    out.hsk_level = display_level_for_row(db, models.Lesson, models.Lesson.hsk_level_id, lesson)
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
    viewer: models.User | None = Depends(get_user_or_none),
):
    query = db.query(models.Lesson)
    if hsk_level is not None:
        level_id, id_subset = resolve_level_filter(db, models.Lesson, models.Lesson.hsk_level_id, hsk_level)
        query = query.filter(models.Lesson.hsk_level_id == (level_id or 0))
        if id_subset is not None:
            query = query.filter(models.Lesson.id.in_(id_subset or [0]))
    lessons = query.order_by(models.Lesson.hsk_level_id, models.Lesson.order_index).all()
    translations = load_translations(db, "lesson", [str(l.id) for l in lessons], locale)
    out = [_localize(db, l, translations) for l in lessons]
    # The catalogue (titles, summaries) stays public, but a lesson's body is
    # only served by GET /{id}, which checks the lesson path -- otherwise
    # this list would hand out every locked lesson's content.
    if not (viewer and viewer.is_admin):
        for item in out:
            item.content = None
    return out


@router.get("/path")
def get_path(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    """The signed-in learner's lesson path: every lesson with its state
    (completed / current / available / locked), grouped by HSK level."""
    state = lesson_path.path_state(db, user)
    translations = load_translations(db, "lesson", [str(e.lesson.id) for e in state.entries], locale)
    levels = []
    for lvl in lesson_path.level_summaries(state):
        entries = lvl.pop("entries")
        lvl["lessons"] = [
            {
                "id": e.lesson.id,
                "title": tr(translations, e.lesson.id, "title", e.lesson.title),
                "summary": tr(translations, e.lesson.id, "summary", e.lesson.summary),
                "lesson_type": e.lesson.lesson_type,
                "status": e.status,
                "practicable": e.practicable,
                "score": e.score,
            }
            for e in entries
        ]
        levels.append(lvl)
    steps = [e for e in state.entries if e.practicable]
    current = state.current
    return {
        "current_lesson_id": current.lesson.id if current else None,
        "current_level": current.level if current else None,
        "completed": sum(1 for e in steps if e.status == lesson_path.COMPLETED),
        "total": len(steps),
        "levels": levels,
    }


@router.post("", response_model=schemas.LessonResponse, status_code=201)
def create_lesson(
    payload: schemas.LessonCreate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
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


def _open_lesson(db: Session, user: models.User, lesson_id: int):
    """(lesson, path entry, None) when the learner may open it, else
    (lesson, None, a 403 lesson_locked response).
    Admins may read any lesson's content (they author it); everyone, admins
    included, still has to pass lessons in order to complete them."""
    lesson = get_or_404(db, models.Lesson, lesson_id)
    state = lesson_path.path_state(db, user)
    entry = state.entry(lesson_id)
    if not user.is_admin and not state.is_open(lesson_id):
        return lesson, None, JSONResponse(status_code=403, content=lesson_path.locked_payload(state))
    return lesson, entry, None


@router.get("/{lesson_id}", response_model=schemas.LessonResponse)
def get_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
    user: models.User = Depends(get_current_user),
):
    lesson, entry, locked = _open_lesson(db, user, lesson_id)
    if locked:
        return locked
    translations = load_translations(db, "lesson", [str(lesson_id)], locale)
    out = _localize(db, lesson, translations)
    # Learners read the lesson without its trailing "New vocabulary:" word
    # list: /items shows those same words as localized cards. Admins author
    # lessons, so they get the stored text whole (a GET -> PUT round trip
    # must never drop the list practice is built from).
    if not user.is_admin:
        out.content = lesson_body(out.content)
    out.path_status = entry.status if entry else None
    return out


@router.get("/{lesson_id}/items")
def get_lesson_items(
    lesson_id: int,
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
    user: models.User = Depends(get_current_user),
):
    """The vocabulary and grammar this lesson teaches (see
    services.practice.lesson_items) -- what its practice round is built from."""
    lesson, _entry, locked = _open_lesson(db, user, lesson_id)
    if locked:
        return locked
    items = lesson_items(db, lesson)
    words, topics = items["vocab"], items["grammar"]
    w_tr = load_translations(db, "vocab_word", [str(w.id) for w in words], locale)
    g_tr = load_translations(db, "grammar_topic", [str(g.id) for g in topics], locale)
    return {
        "vocab": [
            {"id": w.id, "simplified": w.simplified, "pinyin": w.pinyin,
             "meanings": tr(w_tr, w.id, "meanings", w.meanings)}
            for w in words
        ],
        "grammar": [
            {"id": g.id, "title": tr(g_tr, g.id, "title", g.title), "pattern": g.pattern}
            for g in topics
        ],
    }


@router.put("/{lesson_id}", response_model=schemas.LessonResponse)
def update_lesson(
    lesson_id: int, payload: schemas.LessonUpdate, db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
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
    lesson_id: int, payload: schemas.LessonPatch, db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
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
def delete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    lesson = get_or_404(db, models.Lesson, lesson_id)
    db.delete(lesson)
    db.commit()