from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services.gamification import check_achievements

router = APIRouter(prefix="/api/achievements", tags=["achievements"])


@router.get("", response_model=list[schemas.AchievementResponse])
def list_achievements(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_achievements(db, user)
    unlocked = {ua.achievement_id: ua.unlocked_at for ua in user.user_achievements}
    out = []
    for ach in db.query(models.Achievement).order_by(models.Achievement.id).all():
        item = schemas.AchievementResponse.model_validate(ach)
        if ach.id in unlocked:
            item.unlocked = True
            item.unlocked_at = unlocked[ach.id]
        out.append(item)
    return out