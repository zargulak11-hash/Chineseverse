from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services import tone_coach as svc
from app.services.gamification import check_achievements

router = APIRouter(prefix="/api/tones", tags=["tones"])


class AttemptPayload(BaseModel):
    item_type: str = Field(pattern="^(vocab|hanzi)$")
    item_id: int = Field(ge=1)
    # Pitch (Hz, 0 = unvoiced) and loudness per 10 ms frame, measured in the
    # browser (frontend/src/pitch.js). No audio is ever uploaded.
    f0: list[float] = Field(min_length=1, max_length=svc.MAX_FRAMES)
    rms: list[float] | None = Field(default=None, max_length=svc.MAX_FRAMES)


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except svc.ToneError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc


@router.get("/next")
def next_item(mode: str = Query("pair", pattern="^(single|pair)$"), user: models.User = Depends(get_current_user),
              db: Session = Depends(get_db), locale: str = Depends(get_locale)):
    return _run(svc.next_item, db, user, mode, locale)


@router.get("/item/{item_type}/{item_id}")
def one_item(item_type: str, item_id: int, user: models.User = Depends(get_current_user),
             db: Session = Depends(get_db), locale: str = Depends(get_locale)):
    """A specific word or character (e.g. from a word card's "practise its tones")."""
    return _run(svc.item, db, user, item_type, item_id, locale)


@router.get("/stats")
def stats(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.stats(db, user)


@router.post("/attempt")
def attempt(payload: AttemptPayload, user: models.User = Depends(get_current_user), db: Session = Depends(get_db),
            locale: str = Depends(get_locale)):
    out = _run(svc.attempt, db, user, payload.item_type, payload.item_id, payload.f0, payload.rms, locale)
    check_achievements(db, user)
    return out
