"""Chinese Sound World places and the learner's speed stages
(services/sound_world.py). A place is PLAYED as a server-graded practice
round (POST /api/practice/sessions {source: "sound", env, stage})."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user
from app.services import sound_world as svc

router = APIRouter(prefix="/api/sound-world", tags=["sound-world"])


@router.get("/places")
def places(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.env_list(db, user)
