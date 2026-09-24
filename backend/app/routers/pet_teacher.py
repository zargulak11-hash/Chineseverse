import random

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services import ai_client
from app.services.activity import log_activity
from app.services.gamification import (
    add_bond_points,
    check_achievements,
    ensure_bond,
    progress_missions,
    reinforce_mistake,
    user_rank,
)
from app.services.localization import load_translations, tr

router = APIRouter(prefix="/api/pet-teacher", tags=["pet-teacher"])


def _normalize(text: str) -> str:
    return "".join((text or "").split()).lower()


@router.get("/lesson", response_model=schemas.PetTeacherCaseResponse)
def get_lesson(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    """The animal makes a deliberate mistake at (or below) the learner's
    current HSK level. Prefers a case not yet taught, so the loop keeps
    introducing new rules instead of repeating the same one forever."""
    level, _mastery = user_rank(db, user)
    taught_ids = {t.case_id for t in user.taught_facts}

    cases = (
        db.query(models.PetTeacherCase)
        .join(models.HSKLevel, models.PetTeacherCase.hsk_level_id == models.HSKLevel.id)
        .filter(models.HSKLevel.level <= level)
        .all()
    )
    if not cases:
        cases = db.query(models.PetTeacherCase).all()
    if not cases:
        raise HTTPException(status_code=404, detail="No Pet Teacher content available yet")

    untaught = [c for c in cases if c.id not in taught_ids]
    pool = untaught or cases
    case = random.choice(pool)

    item = schemas.PetTeacherCaseResponse.model_validate(case)
    item.already_taught = case.id in taught_ids
    case_tr = load_translations(db, "pet_teacher_case", [str(case.id)], locale)
    item.hint = tr(case_tr, case.id, "hint", item.hint)
    return item


@router.post("/lesson/{case_id}/answer", response_model=schemas.PetTeacherResultResponse)
def answer_lesson(
    case_id: int,
    payload: schemas.PetTeacherAnswerRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    case = db.get(models.PetTeacherCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    correct_fix = _normalize(payload.correction) == _normalize(case.correct_sentence)
    verdict = ai_client.evaluate_pet_teacher_explanation(
        case.mistake_summary or "", payload.explanation, case.explanation_keywords or []
    )
    understood = verdict["understood"]
    success = correct_fix and understood

    ensure_bond(db, user)
    if success:
        already = (
            db.query(models.UserTaughtFact)
            .filter_by(user_id=user.id, case_id=case.id)
            .first()
        )
        if already is None:
            db.add(models.UserTaughtFact(user_id=user.id, case_id=case.id))
        add_bond_points(user, points=5)
        progress_missions(db, user, "teach")
        if case.grammar_topic_id:
            topic = db.get(models.GrammarTopic, case.grammar_topic_id)
            if topic:
                reinforce_mistake(db, user, "grammar", topic.title)
    log_activity(db, user, "pet_teacher_answer")
    db.commit()

    taught_count = db.query(models.UserTaughtFact).filter_by(user_id=user.id).count()
    newly = check_achievements(db, user)

    ui_tr = load_translations(db, "ui_string", ["pet_teacher"], locale)
    feedback = verdict["feedback"]
    if not feedback:
        if success:
            feedback = tr(ui_tr, "pet_teacher", "success",
                           "Perfect — you fixed it and explained why. Your companion just learned something!")
        elif not correct_fix:
            feedback = tr(ui_tr, "pet_teacher", "wrong_correction",
                           "The correction isn't quite right yet — look at the sentence again.")
        else:
            feedback = tr(ui_tr, "pet_teacher", "needs_more_explanation",
                           "The correction is right, but explain the rule a bit more so it really sticks.")
    if newly:
        unlocked_label = tr(ui_tr, "pet_teacher", "unlocked", "Unlocked")
        feedback += f" {unlocked_label}: {', '.join(a.title for a in newly)}"

    case_tr = load_translations(db, "pet_teacher_case", [str(case.id)], locale)
    mistake_summary = tr(case_tr, case.id, "mistake_summary", case.mistake_summary)

    return schemas.PetTeacherResultResponse(
        correct_fix=correct_fix,
        understood=understood,
        success=success,
        correct_sentence=case.correct_sentence,
        mistake_summary=mistake_summary,
        feedback=feedback,
        taught_count=taught_count,
    )
