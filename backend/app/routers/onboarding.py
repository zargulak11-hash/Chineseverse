from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.routers.duels import _build_questions
from app.services.gamification import ensure_user_skills, user_rank

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

# The placement test only spans HSK1-4: HSK5/6 vocab is a thin, low-confidence
# sample (see the HSK data-accuracy pass), so drawing placement questions from
# those levels would risk repeating the same handful of words across attempts.
# A learner who aces HSK1-4 places at HSK4 and progresses into 5/6 normally.
MAX_TEST_LEVEL = 4
PASS_THRESHOLD = 0.6


def _get_or_create_profile(db: Session, user: models.User) -> models.UserProfile:
    profile = user.profile
    if profile is None:
        profile = models.UserProfile(user_id=user.id)
        db.add(profile)
        db.flush()
    return profile


@router.post("/placement-test/start", response_model=schemas.PlacementStartResponse)
def start_placement_test(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    levels = (
        db.query(models.HSKLevel)
        .filter(models.HSKLevel.level <= MAX_TEST_LEVEL)
        .order_by(models.HSKLevel.level)
        .all()
    )
    if not levels:
        raise HTTPException(status_code=500, detail="No HSK levels seeded")

    all_questions = []
    for hsk in levels:
        questions = _build_questions(db, hsk.id, focus_type="meaning")
        for q in questions:
            q["level"] = hsk.level
        all_questions.extend(questions)
    for i, q in enumerate(all_questions):
        q["index"] = i

    attempt = models.PlacementAttempt(
        user_id=user.id,
        status="active",
        question_data=all_questions,
        started_at=datetime.utcnow(),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return schemas.PlacementStartResponse(
        attempt_id=attempt.id,
        questions=[
            schemas.PlacementQuestion(
                index=q["index"], level=q["level"], type=q["type"],
                prompt=q["prompt"], options=q["options"], tts_text=q["tts_text"],
            )
            for q in all_questions
        ],
    )


def _score_and_place(db: Session, user: models.User, attempt: models.PlacementAttempt) -> tuple[int, int]:
    """Grades attempt.question_data (already scored into attempt.correct_count
    per-question via the caller) and sets UserSkill.mastery so the app's
    existing user_rank() threshold logic derives the right starting level --
    no separate placement/unlock formula is introduced."""
    by_level: dict[int, list[bool]] = {}
    for q in attempt.question_data:
        by_level.setdefault(q["level"], []).append(q["_correct"])

    passed_count = 0
    frac_at_fail = 0.0
    for level in range(1, MAX_TEST_LEVEL + 1):
        results = by_level.get(level, [])
        accuracy = (sum(results) / len(results)) if results else 0.0
        if accuracy >= PASS_THRESHOLD:
            passed_count += 1
        else:
            frac_at_fail = accuracy
            break

    if passed_count >= MAX_TEST_LEVEL:
        target_mastery = MAX_TEST_LEVEL * 15 - 1
    else:
        target_mastery = passed_count * 15 + frac_at_fail * 15

    ensure_user_skills(db, user)
    for skill in user.user_skills:
        skill.mastery = target_mastery
    db.commit()

    current_level, overall_mastery = user_rank(db, user)
    return current_level, overall_mastery


@router.post("/placement-test/{attempt_id}/submit", response_model=schemas.PlacementResultResponse)
def submit_placement_test(
    attempt_id: int,
    payload: schemas.PlacementSubmitRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attempt = db.get(models.PlacementAttempt, attempt_id)
    if attempt is None or attempt.user_id != user.id:
        raise HTTPException(status_code=404, detail="Placement attempt not found")
    if attempt.status != "active":
        raise HTTPException(status_code=409, detail="Placement attempt already finished")

    submitted = {a.index: a.answer for a in payload.answers}
    correct_count = 0
    for q in attempt.question_data:
        given = (submitted.get(q["index"]) or "").strip().lower()
        is_correct = given == str(q["answer"]).strip().lower()
        q["_correct"] = is_correct
        if is_correct:
            correct_count += 1
    total_count = len(attempt.question_data)

    current_level, overall_mastery = _score_and_place(db, user, attempt)

    attempt.correct_count = correct_count
    attempt.total_count = total_count
    attempt.placed_level = current_level
    attempt.overall_mastery = overall_mastery
    attempt.status = "finished"
    attempt.finished_at = datetime.utcnow()

    profile = _get_or_create_profile(db, user)
    profile.level_test_score = correct_count
    profile.onboarding_completed = True
    db.commit()

    return schemas.PlacementResultResponse(
        attempt_id=attempt.id,
        correct_count=correct_count,
        total_count=total_count,
        placed_level=current_level,
        overall_mastery=overall_mastery,
    )


@router.post("/placement-test/skip", response_model=schemas.PlacementResultResponse)
def skip_placement_test(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_user_skills(db, user)
    current_level, overall_mastery = user_rank(db, user)

    attempt = models.PlacementAttempt(
        user_id=user.id,
        status="skipped",
        correct_count=0,
        total_count=0,
        placed_level=current_level,
        overall_mastery=overall_mastery,
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    db.add(attempt)

    profile = _get_or_create_profile(db, user)
    profile.onboarding_completed = True
    db.commit()
    db.refresh(attempt)

    return schemas.PlacementResultResponse(
        attempt_id=attempt.id,
        correct_count=0,
        total_count=0,
        placed_level=current_level,
        overall_mastery=overall_mastery,
    )
