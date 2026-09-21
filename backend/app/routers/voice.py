from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services import voice_eval
from app.services.dna import apply_voice_to_skills
from app.services.gamification import (
    check_achievements,
    ensure_user_skills,
    progress_quests,
    touch_streak,
)

router = APIRouter(prefix="/api/voice", tags=["voice"])


class SimpleEvaluate(BaseModel):
    prompt_text: str
    spoken_text: str
    expected_keywords: list[str] = []
    scenario_id: int | None = None
    dialogue_id: int | None = None


class ReactionResponse(BaseModel):
    reaction: str
    evaluation: dict
    scores: dict


@router.post("/attempt", response_model=schemas.VoiceResultResponse)
def submit_attempt(
    payload: schemas.VoiceAttemptCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_user_skills(db, user)

    dialogue = None
    if payload.dialogue_id:
        dialogue = db.get(models.Dialogue, payload.dialogue_id)

    result = voice_eval.grade_turn(
        dialogue, payload.spoken_text,
        expected_keywords=payload.expected_keywords or None,
    )

    attempt = models.VoiceAttempt(
        user_id=user.id,
        scenario_id=payload.scenario_id,
        dialogue_id=payload.dialogue_id,
        prompt_text=payload.prompt_text or result["prompt_text"],
        spoken_text=payload.spoken_text,
        transcript=result["transcript"],
        pronunciation=result["pronunciation"],
        tones=result["tones"],
        fluency=result["fluency"],
        grammar=result["grammar"],
        relevance=result["relevance"],
        response_time_ms=payload.response_time_ms,
        overall=result["overall"],
        feedback=result["feedback"],
    )
    db.add(attempt)
    db.flush()

    apply_voice_to_skills(user, attempt)
    progress_quests(db, user, "speaking", amount=1)
    if user.streak:
        touch_streak(user)

    db.commit()
    db.refresh(attempt)
    db.refresh(user)

    newly = check_achievements(db, user)
    skill_delta = {
        "speaking": min(100.0, round(result["overall"] * 0.5, 1)),
        "tones": min(100.0, round(result["tones"] * 0.3, 1)),
    }
    improvement = None
    if newly:
        improvement = f"Unlocked: {', '.join(a.title for a in newly)}"

    return schemas.VoiceResultResponse(
        attempt=attempt,
        reaction=result["reaction"] or "很好！",
        skill_delta=skill_delta,
        improvement=improvement,
    )


@router.post("/evaluate", response_model=ReactionResponse)
def evaluate_turn(
    payload: SimpleEvaluate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lightweight turn grading for conversations."""
    ensure_user_skills(db, user)
    dialogue = None
    if payload.dialogue_id:
        dialogue = db.get(models.Dialogue, payload.dialogue_id)
    result = voice_eval.grade_turn(
        dialogue, payload.spoken_text,
        expected_keywords=payload.expected_keywords or None,
    )
    return ReactionResponse(
        reaction=result["reaction"] or "很好！",
        evaluation=result["feedback"],
        scores={
            "pronunciation": result["pronunciation"],
            "tones": result["tones"],
            "fluency": result["fluency"],
            "grammar": result["grammar"],
            "relevance": result["relevance"],
            "overall": result["overall"],
        },
    )


@router.get("/history", response_model=list[schemas.VoiceAttemptResponse])
def voice_history(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.VoiceAttempt)
        .filter(models.VoiceAttempt.user_id == user.id)
        .order_by(models.VoiceAttempt.created_at.desc())
        .limit(30)
        .all()
    )