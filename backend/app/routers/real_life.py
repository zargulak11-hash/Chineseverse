"""Real Chinese: real-life situations at the learner's own level.

Read-only browsing endpoints. A scene is PLAYED through the graded
practice engine (POST /api/practice/sessions {source: "scene", scene}),
so this router never grades or writes progress itself."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services import real_life as svc

router = APIRouter(prefix="/api/real-life", tags=["real-life"])


@router.get("/scenes")
def list_scenes(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    return svc.scene_list(db, user, locale)


@router.get("/scenes/{slug}")
def scene_detail(
    slug: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    try:
        return svc.scene_preview(db, user, slug, locale)
    except svc.SceneError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc
