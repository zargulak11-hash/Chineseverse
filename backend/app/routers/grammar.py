from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services.activity import log_activity
from app.services.dna import bump_skill
from app.services.hsk_band import resolve_level_filter
from app.services.localization import load_translations, tr
from app.services.gamification import (
    check_achievements,
    ensure_user_skills,
    memory_multiplier,
    progress_missions,
    progress_quests,
    record_mistake,
    reinforce_mistake,
)

router = APIRouter(prefix="/api/grammar", tags=["grammar"])


class PracticePayload(BaseModel):
    correct: bool
    delta: float = Field(default=10.0, ge=0, le=100)


class PracticeResponse(BaseModel):
    topic: schemas.GrammarTopicWithStatus
    mastery: float
    status: str


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
        out.append(item)
    out.sort(key=lambda t: (not t.due_for_review, t.hsk_level_id, t.id))
    return out


@router.post("/{topic_id}/practice", response_model=PracticeResponse)
def practice_topic(
    topic_id: int,
    payload: PracticePayload,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    topic = db.get(models.GrammarTopic, topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Grammar topic not found")

    rec = (
        db.query(models.UserGrammar)
        .filter_by(user_id=user.id, topic_id=topic_id)
        .first()
    )
    if rec is None:
        rec = models.UserGrammar(
            user_id=user.id, topic_id=topic_id,
            times_practiced=0, times_missed=0, mastery=0.0, status="new",
        )
        db.add(rec)

    rec.times_practiced += 1
    now = datetime.utcnow()
    if payload.correct:
        rec.mastery = min(100.0, rec.mastery + payload.delta)
        multiplier = memory_multiplier(user)
        prev_interval = (
            rec.next_review_at - rec.last_reviewed_at
            if rec.next_review_at and rec.last_reviewed_at
            else None
        )
        prev_base = prev_interval / multiplier if prev_interval and prev_interval.total_seconds() > 0 else None
        base = prev_base * 2 if prev_base else timedelta(days=1)
        interval = min(timedelta(days=30), base)
        rec.next_review_at = now + interval * multiplier
    else:
        rec.times_missed += 1
        rec.mastery = max(0.0, rec.mastery - payload.delta * 0.5)
        rec.next_review_at = now + timedelta(hours=6)

    if rec.mastery >= 85:
        rec.status = "mastered"
    elif rec.mastery >= 55:
        rec.status = "reviewing"
    else:
        rec.status = "learning"

    rec.last_reviewed_at = now

    ensure_user_skills(db, user)
    bump_skill(user, "grammar", 2.0 if payload.correct else -0.3)

    if payload.correct:
        progress_quests(db, user, "grammar", amount=1)
        progress_missions(db, user, "grammar")
        reinforce_mistake(db, user, "grammar", topic.title)
    else:
        record_mistake(
            db, user, "grammar", topic.title,
            question_text=topic.pattern or topic.title, correct_answer=topic.examples,
        )

    log_activity(db, user, "grammar_practice")
    db.commit()
    db.refresh(rec)
    check_achievements(db, user)

    topic_out = schemas.GrammarTopicWithStatus.model_validate(topic)
    translations = load_translations(db, "grammar_topic", [str(topic.id)], locale)
    topic_out.title = tr(translations, topic.id, "title", topic_out.title)
    topic_out.explanation = tr(translations, topic.id, "explanation", topic_out.explanation)
    topic_out.category = tr(translations, topic.id, "category", topic_out.category)
    topic_out.difficulty = tr(translations, topic.id, "difficulty", topic_out.difficulty)
    topic_out.status = rec.status
    topic_out.mastery = rec.mastery
    return PracticeResponse(topic=topic_out, mastery=round(rec.mastery, 1), status=rec.status)
