"""Chinese Stories (services/stories.py) and the learner's journey (services/journey.py)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services import journey as journey_svc
from app.services import stories as svc

router = APIRouter(prefix="/api/stories", tags=["stories"])
journey_router = APIRouter(prefix="/api/journey", tags=["journey"])


@router.get("")
def list_stories(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    return svc.library(db, user, locale)


@router.get("/{slug}")
def read_story(
    slug: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    try:
        return svc.view(db, user, slug, locale)
    except svc.StoryError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc


@journey_router.get("")
def my_journey(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Where the learner is, the one thing to do next, and the road ahead --
    all from their own records."""
    return journey_svc.journey(db, user)
