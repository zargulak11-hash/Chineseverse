from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services.gamification import (
    check_achievements,
    ensure_user_skills,
    memory_multiplier,
    progress_missions,
    progress_quests,
    record_mistake,
    reinforce_mistake,
)

router = APIRouter(prefix="/api/vocab", tags=["vocabulary"])


class ReviewPayload(BaseModel):
    correct: bool
    delta: float = Field(default=10.0, ge=0, le=100)


class ReviewResponse(BaseModel):
    word: schemas.WordWithStatus
    mastery: float
    status: str


@router.get("", response_model=list[schemas.WordWithStatus])
def list_words(
    hsk_level: int | None = None,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_user_skills(db, user)
    query = db.query(models.VocabularyWord)
    if hsk_level is not None:
        query = query.join(models.HSKLevel, models.VocabularyWord.hsk_level_id == models.HSKLevel.id)
        query = query.filter(models.HSKLevel.level == hsk_level)
    words = query.order_by(models.VocabularyWord.id).all()

    user_map = {w.word_id: w for w in user.user_vocabulary}
    now = datetime.utcnow()
    out = []
    for word in words:
        item = schemas.WordWithStatus.model_validate(word)
        rec = user_map.get(word.id)
        item.status = rec.status if rec else "new"
        item.mastery = rec.mastery if rec else 0.0
        item.due_for_review = bool(rec and rec.next_review_at and rec.next_review_at <= now)
        out.append(item)
    # Resurface what's actually due first, instead of a fixed id order —
    # this is the "Memory of the World" reading the schedule it writes.
    out.sort(key=lambda w: (not w.due_for_review, w.id))
    return out


@router.post("/{word_id}/review", response_model=ReviewResponse)
def review_word(
    word_id: int,
    payload: ReviewPayload,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    word = db.get(models.VocabularyWord, word_id)
    if word is None:
        raise HTTPException(status_code=404, detail="Word not found")

    rec = (
        db.query(models.UserVocabulary)
        .filter_by(user_id=user.id, word_id=word_id)
        .first()
    )
    if rec is None:
        rec = models.UserVocabulary(
            user_id=user.id, word_id=word_id,
            times_seen=0, times_missed=0, mastery=0.0, status="new",
        )
        db.add(rec)

    rec.times_seen += 1
    now = datetime.utcnow()
    if payload.correct:
        rec.mastery = min(100.0, rec.mastery + payload.delta)
        # Exponential backoff: each correct review roughly doubles the gap
        # since the last one (capped at 30 days), instead of a fixed
        # interval — a genuinely spaced schedule, not a 3-tier bucket.
        multiplier = memory_multiplier(user)
        prev_interval = (
            rec.next_review_at - rec.last_reviewed_at
            if rec.next_review_at and rec.last_reviewed_at
            else None
        )
        # Undo the previous step's animal multiplier before doubling, so
        # the multiplier is always a flat bonus on top of a plain 2x
        # doubling — not compounding into an ever-growing extra bonus.
        prev_base = prev_interval / multiplier if prev_interval and prev_interval.total_seconds() > 0 else None
        base = prev_base * 2 if prev_base else timedelta(days=1)
        interval = min(timedelta(days=30), base)
        rec.next_review_at = now + interval * multiplier
    else:
        rec.times_missed += 1
        rec.mastery = max(0.0, rec.mastery - payload.delta * 0.5)
        # Reset to a short cycle on failure, regardless of prior progress.
        rec.next_review_at = now + timedelta(hours=6)

    if rec.mastery >= 85:
        rec.status = "mastered"
    elif rec.mastery >= 55:
        rec.status = "reviewing"
    else:
        rec.status = "learning"

    rec.last_reviewed_at = now

    if payload.correct:
        progress_quests(db, user, "vocab", amount=1)
        progress_missions(db, user, "vocab")
        reinforce_mistake(db, user, "word", word.simplified)
    else:
        record_mistake(
            db, user, "word", word.simplified,
            question_text=word.meanings, correct_answer=word.pinyin,
        )

    streak = user.streak
    if streak is None:
        from datetime import date
        streak = models.UserStreak(user_id=user.id, last_active_date=date.today())
        db.add(streak)
    streak.total_active_days = max(
        1, streak.total_active_days if streak.total_active_days else 1
    )

    db.commit()
    db.refresh(rec)
    check_achievements(db, user)
    return ReviewResponse(
        word=schemas.WordWithStatus.model_validate(word),
        mastery=round(rec.mastery, 1),
        status=rec.status,
    )