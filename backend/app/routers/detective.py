"""Detective Mode case files (services/detective.py).

Browsing only: a case is PLAYED as a server-graded practice round
(POST /api/practice/sessions {source: "detective", case}) -- a generated
structure ("who_took") or a hand-written case file ("file:<slug>"). Reading
a case file writes nothing."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services import detective as svc

router = APIRouter(prefix="/api/detective", tags=["detective"])


@router.get("/cases")
def cases(
    level: int | None = Query(None, ge=1, le=9),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    return svc.case_list(db, user, locale, level)


@router.get("/files/{slug}")
def case_file(
    slug: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    try:
        return svc.dossier(db, user, slug, locale)
    except svc.CaseError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc
