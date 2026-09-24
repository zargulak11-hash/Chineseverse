from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services import voice_eval
from app.services.activity import log_activity
from app.services.dna import apply_voice_to_skills
from app.services.ai_client import chat_reply
from app.services.gamification import (
    check_achievements,
    ensure_user_skills,
    progress_missions,
    progress_quests,
    record_mistake,
    reinforce_mistake,
    scenario_is_unlocked,
    touch_streak,
    user_rank,
)

MISTAKE_WEAK_THRESHOLD = 70.0

router = APIRouter(prefix="/api/voice", tags=["voice"])


def _track_mistake(db: Session, user: models.User, prompt_text: str | None, result: dict) -> None:
    """Feed the weakest skill signal from this attempt into the mistake memory."""
    scored = {
        "pinyin": result["pronunciation"],
        "tone": result["tones"],
        "grammar": result["grammar"],
        "word": result["relevance"],
    }
    mistake_type, worst = min(scored.items(), key=lambda kv: kv[1])
    reference = prompt_text or result.get("prompt_text") or result.get("transcript") or "practice"
    if worst < MISTAKE_WEAK_THRESHOLD:
        record_mistake(
            db, user, mistake_type, reference,
            question_text=prompt_text or result.get("prompt_text"),
            answer_given=result.get("transcript"),
        )
    else:
        reinforce_mistake(db, user, mistake_type, reference)


class VoiceCompanionTurn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=2000)


class VoiceCompanionChatRequest(BaseModel):
    # animal_id picks who narrates THIS voice session only -- it is never
    # written to user.animal_id / UserAnimal / anywhere the main learning
    # companion lives. See submit_companion_chat below.
    animal_id: int
    spoken_text: str = Field(min_length=1, max_length=1000)
    history: list[VoiceCompanionTurn] = Field(default_factory=list, max_length=20)
    response_time_ms: int = Field(default=0, ge=0)


class VoiceCompanionInfo(BaseModel):
    id: int
    slug: str
    name: str


class VoiceCompanionChatResponse(BaseModel):
    attempt: schemas.VoiceAttemptResponse
    companion: VoiceCompanionInfo
    companion_reply: str
    skill_delta: dict[str, float]
    improvement: str | None = None


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

    if payload.scenario_id:
        scenario = db.get(models.Scenario, payload.scenario_id)
        if scenario is not None and not scenario_is_unlocked(db, user, scenario):
            raise HTTPException(status_code=403, detail="This location isn't unlocked yet")

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
    progress_missions(db, user, "listening")
    if payload.scenario_id:
        progress_missions(db, user, "speak", scenario_id=payload.scenario_id)
        progress_missions(db, user, "conversation", scenario_id=payload.scenario_id)
    _track_mistake(db, user, payload.prompt_text, result)
    if user.streak:
        touch_streak(user)
    log_activity(db, user, "voice_attempt")

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


@router.post("/companion-chat", response_model=VoiceCompanionChatResponse)
def submit_companion_chat(
    payload: VoiceCompanionChatRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Daily Voice Companion turn: `payload.animal_id` picks who the user is
    talking to for THIS conversation only -- a request-level choice, never
    persisted anywhere near the user's actual companion (user.animal_id /
    UserAnimal). Real evaluation, DNA, mistakes and quests are all the same
    machinery /attempt already uses; the only new part is generating the
    chosen animal's in-character reply via the (already-existing, previously
    unused) ai_client.chat_reply."""
    ensure_user_skills(db, user)

    animal = db.get(models.Animal, payload.animal_id)
    if animal is None:
        raise HTTPException(status_code=404, detail="Animal not found")
    personality_row = animal.personality_row

    result = voice_eval.grade_turn(None, payload.spoken_text, expected_keywords=None)

    attempt = models.VoiceAttempt(
        user_id=user.id,
        scenario_id=None,
        dialogue_id=None,
        prompt_text=None,
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
    progress_missions(db, user, "listening")
    _track_mistake(db, user, None, result)
    if user.streak:
        touch_streak(user)
    log_activity(db, user, "voice_attempt")

    hsk_level, _ = user_rank(db, user)
    level_hint = "beginner" if hsk_level <= 2 else "intermediate" if hsk_level <= 4 else "advanced"

    personality_desc = " ".join(filter(None, [animal.personality, animal.tone_style]))
    reply = chat_reply(
        [t.model_dump() for t in payload.history] + [{"role": "user", "content": payload.spoken_text}],
        companion=animal.name,
        user_name=user.username,
        personality=personality_desc or None,
        catchphrase=personality_row.catchphrase if personality_row else None,
        energy=personality_row.energy if personality_row else None,
        level_hint=level_hint,
    )

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

    return VoiceCompanionChatResponse(
        attempt=attempt,
        companion=VoiceCompanionInfo(id=animal.id, slug=animal.slug, name=animal.name),
        companion_reply=reply,
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
        evaluation={
            "feedback": result["feedback"],
            "prompt": result["prompt_text"],
            "transcript": result["transcript"],
            "is_correct": result["is_correct"],
        },
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