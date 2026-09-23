from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud import get_or_404
from app.database import get_db
from app.deps import get_current_user
from app.services.gamification import check_achievements

router = APIRouter(prefix="/api/mistakes", tags=["mistakes"])


def _serialize(m: models.LearningMistake) -> schemas.MistakeResponse:
    out = schemas.MistakeResponse.model_validate(m)
    out.due_for_review = bool(
        not m.mastered and m.next_review_at and m.next_review_at <= datetime.utcnow()
    )
    return out


@router.get("", response_model=list[schemas.MistakeResponse])
def list_mistakes(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_achievements(db, user)
    rows = (
        db.query(models.LearningMistake)
        .filter(models.LearningMistake.user_id == user.id)
        .order_by(models.LearningMistake.priority.desc())
        .limit(50)
        .all()
    )
    return [_serialize(m) for m in rows]


@router.patch("/{mistake_id}", response_model=schemas.MistakeResponse)
def patch_mistake(
    mistake_id: int,
    payload: schemas.MistakePatch,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mistake = (
        db.query(models.LearningMistake)
        .filter(models.LearningMistake.id == mistake_id, models.LearningMistake.user_id == user.id)
        .first()
    )
    if mistake is None:
        get_or_404(db, models.LearningMistake, mistake_id)
    if payload.request_retest:
        # Bump it to the front of the review queue — this does NOT grant
        # mastery. Mastery only ever comes from reinforce_mistake(), which
        # fires when the learner actually answers this reference correctly
        # again through voice, vocab review, a case, or a duel.
        mistake.next_review_at = datetime.utcnow()
    db.commit()
    db.refresh(mistake)
    check_achievements(db, user)
    return _serialize(mistake)
