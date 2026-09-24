from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services.gamification import check_achievements
from app.services.localization import load_translations, tr

router = APIRouter(prefix="/api/achievements", tags=["achievements"])


@router.get("", response_model=list[schemas.AchievementResponse])
def list_achievements(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    check_achievements(db, user)
    unlocked = {ua.achievement_id: ua.unlocked_at for ua in user.user_achievements}
    achievements = db.query(models.Achievement).order_by(models.Achievement.id).all()
    translations = load_translations(db, "achievement", [str(a.id) for a in achievements], locale)
    out = []
    for ach in achievements:
        item = schemas.AchievementResponse.model_validate(ach)
        item.title = tr(translations, ach.id, "title", item.title)
        item.description = tr(translations, ach.id, "description", item.description)
        if ach.id in unlocked:
            item.unlocked = True
            item.unlocked_at = unlocked[ach.id]
        out.append(item)
    return out