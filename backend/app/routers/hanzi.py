from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
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

router = APIRouter(prefix="/api/hanzi", tags=["hanzi"])


class ReviewPayload(BaseModel):
    correct: bool
    delta: float = Field(default=10.0, ge=0, le=100)


class ReviewResponse(BaseModel):
    hanzi: schemas.HanziWithStatus
    mastery: float
    status: str


class WritePayload(BaseModel):
    # Real results from a completed HanziWriter stroke-order quiz against
    # this character's actual stroke_data -- totalMistakes is HanziWriter's
    # own count of incorrect strokes before each one was matched correctly.
    # This endpoint is only reachable after every real stroke was traced and
    # validated; there is no "mark as written" shortcut.
    total_mistakes: int = Field(ge=0)


class WriteResponse(BaseModel):
    hanzi: schemas.HanziWithStatus
    writing_mastery: float
    writing_status: str


@router.get("", response_model=list[schemas.HanziWithStatus])
def list_hanzi(
    hsk_level: int | None = None,
    handwriting_only: bool = False,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    """Recognition-tracked Hanzi list. `handwriting_only` filters to
    characters the real HSK 3.0 syllabus actually requires handwriting for.
    Use GET /{hanzi_id}/stroke-data + POST /{hanzi_id}/write for the real
    tracing quiz on those characters."""
    ensure_user_skills(db, user)
    query = db.query(models.Hanzi)
    if hsk_level is not None:
        level_id, id_subset = resolve_level_filter(db, models.Hanzi, models.Hanzi.hsk_level_id, hsk_level)
        query = query.filter(models.Hanzi.hsk_level_id == (level_id or 0))
        if id_subset is not None:
            query = query.filter(models.Hanzi.id.in_(id_subset or [0]))
    if handwriting_only:
        query = query.filter(models.Hanzi.handwriting_tier.isnot(None))
    items = query.order_by(models.Hanzi.hsk_level_id, models.Hanzi.order_index, models.Hanzi.id).all()

    # Only `meaning` is localized -- the character and pinyin stay as-is.
    translations = load_translations(db, "hanzi", [str(h.id) for h in items], locale)
    user_map = {r.hanzi_id: r for r in user.user_hanzi}
    now = datetime.utcnow()
    out = []
    for h in items:
        item = schemas.HanziWithStatus.model_validate(h)
        item.meaning = tr(translations, h.id, "meaning", item.meaning)
        rec = user_map.get(h.id)
        item.status = rec.status if rec else "new"
        item.mastery = rec.mastery if rec else 0.0
        item.due_for_review = bool(rec and rec.next_review_at and rec.next_review_at <= now)
        item.writing_status = rec.writing_status if rec else "not_practiced"
        item.writing_mastery = rec.writing_mastery if rec else 0.0
        out.append(item)
    out.sort(key=lambda h: (not h.due_for_review, h.hsk_level_id, h.id))
    return out


@router.get("/{hanzi_id}/stroke-data", response_model=schemas.HanziStrokeData)
def get_stroke_data(
    hanzi_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Real stroke path/median vector data for the tracing quiz -- kept out
    of the list endpoint because it's heavy, fetched on demand per character."""
    h = db.get(models.Hanzi, hanzi_id)
    if h is None:
        raise HTTPException(status_code=404, detail="Hanzi not found")
    return schemas.HanziStrokeData.model_validate(h)


@router.get("/{hanzi_id}/examples", response_model=list[schemas.WordResponse])
def get_examples(
    hanzi_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    """Real words from the already-imported vocabulary that actually contain
    this character (e.g. 你 -> 你好/你们/你是) -- never invented example
    sentences. Shortest/most basic words first (short + low HSK level is a
    reasonable proxy for "more elementary"), capped at 5 so this stays a
    quick reference, not a second vocabulary browser."""
    h = db.get(models.Hanzi, hanzi_id)
    if h is None:
        raise HTTPException(status_code=404, detail="Hanzi not found")

    words = (
        db.query(models.VocabularyWord)
        .filter(models.VocabularyWord.simplified.contains(h.character))
        .join(models.HSKLevel, models.VocabularyWord.hsk_level_id == models.HSKLevel.id)
        .order_by(func.length(models.VocabularyWord.simplified), models.HSKLevel.level)
        .limit(5)
        .all()
    )
    translations = load_translations(db, "vocab_word", [str(w.id) for w in words], locale)
    out = []
    for w in words:
        item = schemas.WordResponse.model_validate(w)
        item.meanings = tr(translations, w.id, "meanings", item.meanings)
        out.append(item)
    return out


@router.post("/{hanzi_id}/review", response_model=ReviewResponse)
def review_hanzi(
    hanzi_id: int,
    payload: ReviewPayload,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    """Recognition review only (e.g. 'do you know this character's meaning /
    pronunciation'). This never marks handwriting as practiced or mastered --
    there is no stroke-tracing exercise wired up yet to earn that claim."""
    h = db.get(models.Hanzi, hanzi_id)
    if h is None:
        raise HTTPException(status_code=404, detail="Hanzi not found")

    rec = (
        db.query(models.UserHanzi)
        .filter_by(user_id=user.id, hanzi_id=hanzi_id)
        .first()
    )
    if rec is None:
        rec = models.UserHanzi(
            user_id=user.id, hanzi_id=hanzi_id,
            times_seen=0, times_missed=0, mastery=0.0, status="new",
        )
        db.add(rec)

    rec.times_seen += 1
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
    # Character recognition is a reading/vocabulary-adjacent skill; there is
    # no dedicated "hanzi" DNA skill (see Skill model), so this feeds
    # "reading" -- the closest existing skill to character recognition,
    # same convention as any other reading-comprehension activity.
    bump_skill(user, "reading", 2.0 if payload.correct else -0.3)

    if payload.correct:
        progress_quests(db, user, "hanzi", amount=1)
        progress_missions(db, user, "hanzi")
        reinforce_mistake(db, user, "hanzi", h.character)
    else:
        record_mistake(
            db, user, "hanzi", h.character,
            question_text=h.meaning, correct_answer=h.pinyin,
        )

    log_activity(db, user, "hanzi_review")
    db.commit()
    db.refresh(rec)
    check_achievements(db, user)

    h_out = schemas.HanziWithStatus.model_validate(h)
    translations = load_translations(db, "hanzi", [str(h.id)], locale)
    h_out.meaning = tr(translations, h.id, "meaning", h_out.meaning)
    h_out.status = rec.status
    h_out.mastery = rec.mastery
    h_out.writing_status = rec.writing_status
    h_out.writing_mastery = rec.writing_mastery
    return ReviewResponse(hanzi=h_out, mastery=round(rec.mastery, 1), status=rec.status)


@router.post("/{hanzi_id}/write", response_model=WriteResponse)
def write_hanzi(
    hanzi_id: int,
    payload: WritePayload,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    """Records a completed HanziWriter stroke-order quiz. Only reachable
    after the learner actually traced every real stroke correctly (per
    HanziWriter's own hit-testing against Hanzi.stroke_data); total_mistakes
    only affects how much writing_mastery is gained, never whether it's
    recorded at all. This is fully separate from recognition mastery."""
    h = db.get(models.Hanzi, hanzi_id)
    if h is None:
        raise HTTPException(status_code=404, detail="Hanzi not found")
    if h.stroke_data is None:
        raise HTTPException(status_code=422, detail="No stroke data available for this character")

    rec = (
        db.query(models.UserHanzi)
        .filter_by(user_id=user.id, hanzi_id=hanzi_id)
        .first()
    )
    if rec is None:
        rec = models.UserHanzi(
            user_id=user.id, hanzi_id=hanzi_id,
            times_seen=0, times_missed=0, mastery=0.0, status="new",
            times_written=0, writing_mastery=0.0, writing_status="not_practiced",
        )
        db.add(rec)

    rec.times_written = (rec.times_written or 0) + 1
    # Fewer real stroke mistakes -> more mastery gained per attempt, but a
    # completed quiz always counts for something (it was still traced
    # correctly in the end, just with retries along the way).
    if payload.total_mistakes == 0:
        gain = 25.0
    elif payload.total_mistakes <= 2:
        gain = 15.0
    else:
        gain = 8.0
    rec.writing_mastery = min(100.0, (rec.writing_mastery or 0.0) + gain)
    rec.last_written_at = datetime.utcnow()
    if rec.writing_mastery >= 85:
        rec.writing_status = "mastered"
    elif rec.writing_mastery >= 40:
        rec.writing_status = "practicing"
    else:
        rec.writing_status = "practicing" if rec.times_written > 0 else "not_practiced"

    ensure_user_skills(db, user)
    bump_skill(user, "writing", 2.0 if payload.total_mistakes <= 2 else 1.0)

    progress_quests(db, user, "hanzi_write", amount=1)
    progress_missions(db, user, "hanzi_write")
    log_activity(db, user, "hanzi_write")
    db.commit()
    db.refresh(rec)
    check_achievements(db, user)

    h_out = schemas.HanziWithStatus.model_validate(h)
    translations = load_translations(db, "hanzi", [str(h.id)], locale)
    h_out.meaning = tr(translations, h.id, "meaning", h_out.meaning)
    h_out.status = rec.status
    h_out.mastery = rec.mastery
    h_out.writing_status = rec.writing_status
    h_out.writing_mastery = rec.writing_mastery
    return WriteResponse(hanzi=h_out, writing_mastery=round(rec.writing_mastery, 1), writing_status=rec.writing_status)
