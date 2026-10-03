"""Chinese Passport (services/passport.py): what the learner can do in
Chinese, with the evidence for each capability and their progress story.
Read-only and always scoped to the signed-in learner."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services import passport as svc

router = APIRouter(prefix="/api/passport", tags=["passport"])


@router.get("")
def my_passport(user: models.User = Depends(get_current_user), db: Session = Depends(get_db),
                locale: str = Depends(get_locale)):
    return svc.passport(db, user, locale)
