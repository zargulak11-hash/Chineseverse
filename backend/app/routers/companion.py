"""The permanent companion's learning memory (services/companion_memory.py).

Read-only: every memory is derived from the learner's own stored activity.
Never touches the Daily Voice Companion, which is session-only."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services import companion_memory
from app.services.gamification import ensure_user_skills

router = APIRouter(prefix="/api/companion", tags=["companion"])


@router.get("/memory")
def memory(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    ensure_user_skills(db, user)
    return companion_memory.memories(db, user, locale)
