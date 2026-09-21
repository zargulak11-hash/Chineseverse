from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud import get_or_404
from app.database import get_db
from app.deps import get_current_user
from app.services.gamification import check_achievements

router = APIRouter(prefix="/api/mistakes", tags=["mistakes"])


@router.get("", response_model=list[schemas.MistakeResponse])
def list_mistakes(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_achievements(db, user)
    return (
        db.query(models.LearningMistake)
        .filter(models.LearningMistake.user_id == user.id)
        .order_by(models.LearningMistake.priority.desc())
        .limit(50)
        .all()
    )


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
    if payload.mastered is not None:
        mistake.mastered = payload.mastered
        from datetime import datetime
        mistake.mastered_at = datetime.utcnow() if payload.mastered else None
    db.commit()
    db.refresh(mistake)
    check_achievements(db, user)
    return mistake