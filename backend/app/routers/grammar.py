from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services.activity import log_activity
from app.services import companion_reaction as cr
from app.services.dna import bump_skill
from app.services.srs import apply_srs
from app.services.hsk_band import resolve_level_filter
from app.services.localization import load_translations, tr
from app.services.gamification import (
    check_achievements,
    ensure_user_skills,
    progress_missions,
    progress_quests,
    record_mistake,
    reinforce_mistake,
)

router = APIRouter(prefix="/api/grammar", tags=["grammar"])


class PracticePayload(BaseModel):
    correct: bool
    # No client-chosen step size: "delta" used to be accepted here (up to 100),
    # so one request with {"correct": true, "delta": 100} marked an item
    # mastered. The step is the server's; an old client still sending
    # "delta" is ignored, not rejected.


class PracticeResponse(BaseModel):
    topic: schemas.GrammarTopicWithStatus
    mastery: float
    status: str
    reaction: dict | None = None  # permanent companion's reaction to this result


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
    status_before = rec.status if rec is not None else None
    if rec is None:
        rec = models.UserGrammar(
            user_id=user.id, topic_id=topic_id,
            times_practiced=0, times_missed=0, mastery=0.0, status="new",
        )
        db.add(rec)

    apply_srs(rec, payload.correct, user, counter="times_practiced")

    ensure_user_skills(db, user)
    skill_before = cr.skill_value(user, "grammar")
    bump_skill(user, "grammar", 2.0 if payload.correct else -0.3)
    skill_up = cr.skill_crossing("grammar", skill_before, cr.skill_value(user, "grammar"))

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
    reaction = cr.self_check_reaction(
        user, item_type="grammar", correct=payload.correct, status_before=status_before, status_after=rec.status,
        times_missed=rec.times_missed or 0, skill=skill_up,
        focus={"item_type": "grammar", "hanzi": topic.pattern or "", "pinyin": "", "meaning": topic_out.title},
    )
    return PracticeResponse(topic=topic_out, mastery=round(rec.mastery, 1), status=rec.status, reaction=reaction)
