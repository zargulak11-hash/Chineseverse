from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services import achievements as svc

router = APIRouter(prefix="/api/achievements", tags=["achievements"])


class SeenPayload(BaseModel):
    ids: list[int] = Field(default_factory=list, max_length=200)


@router.get("", response_model=list[schemas.AchievementResponse])
def list_achievements(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    """Every achievement with the signed-in learner's real progress."""
    svc.check(db, user)
    return svc.responses(db, svc.overview(db, user), locale)


@router.post("/seen")
def mark_seen(
    payload: SeenPayload,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The unlock note for these achievements was shown. Only marks the
    caller's own unlocks; it can never unlock anything."""
    return {"marked": svc.mark_seen(db, user, payload.ids)}
