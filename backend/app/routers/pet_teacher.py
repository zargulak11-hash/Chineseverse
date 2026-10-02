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
        # Nothing at or below the learner's level yet: the easiest cases,
        # not every case (answer_lesson accepts the same reach).
        lowest = (
            db.query(models.HSKLevel.level)
            .join(models.PetTeacherCase, models.PetTeacherCase.hsk_level_id == models.HSKLevel.id)
            .order_by(models.HSKLevel.level)
            .first()
        )
        if lowest:
            cases = (
                db.query(models.PetTeacherCase)
                .join(models.HSKLevel, models.PetTeacherCase.hsk_level_id == models.HSKLevel.id)
                .filter(models.HSKLevel.level == lowest[0])
                .all()
            )
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
    # GET /lesson only hands out cases at or below the learner's level; an
    # answer to a higher one is refused the same way, not taught.
    level, _mastery = user_rank(db, user)
    lowest = (
        db.query(models.HSKLevel.level)
        .join(models.PetTeacherCase, models.PetTeacherCase.hsk_level_id == models.HSKLevel.id)
        .order_by(models.HSKLevel.level)
        .first()
    )
    # Same reach as GET /lesson, including its "nothing at your level yet"
    # fallback to the easiest cases.
    allowed = max(level, lowest[0] if lowest else level)
    case_level = db.get(models.HSKLevel, case.hsk_level_id)
    if case_level is not None and case_level.level > allowed:
        raise HTTPException(status_code=403, detail="This case is above your current HSK level")

    correct_fix = _normalize(payload.correction) == _normalize(case.correct_sentence)
    verdict = ai_client.evaluate_pet_teacher_explanation(
        case.mistake_summary or "", payload.explanation, case.explanation_keywords or []
    )
    understood = verdict["understood"]
    success = correct_fix and understood

    if success:
        already = (
            db.query(models.UserTaughtFact)
            .filter_by(user_id=user.id, case_id=case.id)
            .first()
        )
        if already is None:
            db.add(models.UserTaughtFact(user_id=user.id, case_id=case.id))
            # Only a newly taught fact earns bond points and moves "teach"
            # missions: re-submitting a case already solved (its answer is
            # known) used to count each time -- a dozen repeats reached bond
            # level 3 and its achievement.
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
