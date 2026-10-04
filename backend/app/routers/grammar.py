from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services import grammar_lesson as gl
from app.services.hsk_band import resolve_level_filter
from app.services.localization import load_translations, tr
from app.services.gamification import ensure_user_skills

router = APIRouter(prefix="/api/grammar", tags=["grammar"])

# Read-only. POST /{topic_id}/practice used to take {"correct": true} from the
# browser and apply it as a graded answer (mastery, DNA, quests, missions).
# No screen called it any more -- grammar is practiced through the
# server-graded rounds in /api/practice -- so it was removed.


@router.get("", response_model=list[schemas.GrammarTopicWithStatus])
def list_grammar(
    hsk_level: int | None = None,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    ensure_user_skills(db, user)
    query = db.query(models.GrammarTopic)
    if hsk_level is not None:
        level_id, id_subset = resolve_level_filter(db, models.GrammarTopic, models.GrammarTopic.hsk_level_id, hsk_level)
        query = query.filter(models.GrammarTopic.hsk_level_id == (level_id or 0))
        if id_subset is not None:
            query = query.filter(models.GrammarTopic.id.in_(id_subset or [0]))
    topics = query.order_by(models.GrammarTopic.hsk_level_id, models.GrammarTopic.order_index).all()

    # Only title/explanation/category/difficulty are localized -- pattern and
    # examples are the real Chinese being taught and stay Chinese in every locale.
    translations = load_translations(db, "grammar_topic", [str(t.id) for t in topics], locale)
    user_map = {r.topic_id: r for r in user.user_grammar}
    lesson_names = gl.names(db, topics, locale)
    now = datetime.utcnow()
    out = []
    for topic in topics:
        item = schemas.GrammarTopicWithStatus.model_validate(topic)
        item.title = tr(translations, topic.id, "title", item.title)
        item.explanation = tr(translations, topic.id, "explanation", item.explanation)
        item.category = tr(translations, topic.id, "category", item.category)
        item.difficulty = tr(translations, topic.id, "difficulty", item.difficulty)
        rec = user_map.get(topic.id)
        item.status = rec.status if rec else "new"
        item.mastery = rec.mastery if rec else 0.0
        item.due_for_review = bool(rec and rec.next_review_at and rec.next_review_at <= now)
        item.name = lesson_names.get(topic.id)
        out.append(item)
    out.sort(key=lambda t: (not t.due_for_review, t.hsk_level_id, t.id))
    return out


class CheckPayload(BaseModel):
    answer: str = Field(min_length=1, max_length=120)
    # Index into the lesson's exercises (a "write" one); None = the learner's
    # own sentence with this pattern.
    exercise: int | None = Field(default=None, ge=0, le=20)


def _run(fn, *args):
    try:
        return fn(*args)
    except gl.GrammarError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc


@router.get("/{topic_id}")
def grammar_page(
    topic_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    """The full learning page of one grammar point (services/grammar_lesson.py)."""
    return _run(gl.page, db, user, topic_id, locale)


@router.post("/{topic_id}/lesson")
def generate_lesson(
    topic_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    """Ask for the AI lesson of a point that has no authored one yet. Cached
    per topic and language, so every later learner gets it without a call."""
    return _run(gl.generate, db, user, topic_id, locale)


@router.post("/{topic_id}/check")
def check_sentence(
    topic_id: int,
    payload: CheckPayload,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    """Check a "try it" sentence. Feedback only -- mastery changes only
    through server-graded practice rounds."""
    return _run(gl.check_answer, db, user, topic_id, payload.answer, payload.exercise, locale)
