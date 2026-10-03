"""Chinese Internet (services/internet.py): curated real-world Chinese,
adapted to the learner. Reading and word help are read-only; the graded
round is POST /api/practice/sessions {source: "internet", item, version}."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services import internet as svc

router = APIRouter(prefix="/api/internet", tags=["internet"])


def _run(fn, *args):
    try:
        return fn(*args)
    except svc.InternetError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc


@router.get("/feed")
def feed(user: models.User = Depends(get_current_user), db: Session = Depends(get_db),
         locale: str = Depends(get_locale)):
    return svc.feed(db, user, locale)


@router.get("/items/{slug}")
def item(slug: str, version: str | None = Query(default=None, max_length=20),
         user: models.User = Depends(get_current_user), db: Session = Depends(get_db),
         locale: str = Depends(get_locale)):
    return _run(svc.item_view, db, user, slug, version, locale)


@router.get("/words/{word_id}")
def word(word_id: int, item: str | None = Query(default=None, max_length=40),
         version: str | None = Query(default=None, max_length=20),
         user: models.User = Depends(get_current_user), db: Session = Depends(get_db),
         locale: str = Depends(get_locale)):
    return _run(svc.word_help, db, user, word_id, item, locale, version)
