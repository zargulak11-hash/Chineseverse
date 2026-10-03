"""Chinese Stories (services/stories.py) and the learner's journey (services/journey.py).

Every route is for the signed-in learner's own reading: progress is keyed
by the token's user, never by an id in the request, and a book above the
learner's HSK level is refused (403) by all of them. Reads (library, book,
chapter) write nothing; progress is written only by a reading action."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services import journey as journey_svc
from app.services import stories as svc

router = APIRouter(prefix="/api/stories", tags=["stories"])
journey_router = APIRouter(prefix="/api/journey", tags=["journey"])


class PositionPayload(BaseModel):
    chapter: int = Field(ge=1, le=200)
    position: int = Field(ge=0, le=5000)


class ChapterPayload(BaseModel):
    chapter: int = Field(ge=1, le=200)


class LookupPayload(BaseModel):
    word_id: int = Field(ge=1)


class ExplainPayload(BaseModel):
    chapter: int = Field(ge=1, le=200)
    text: str = Field(min_length=1, max_length=400)
    focus: str = Field(default="explain", max_length=12)


def _run(fn, *args):
    try:
        return fn(*args)
    except svc.StoryError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc


@router.get("")
def list_stories(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    return svc.library(db, user, locale)


@router.get("/{slug}")
def read_book(
    slug: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    return _run(svc.view, db, user, slug, locale)


@router.get("/{slug}/chapters/{n}")
def read_chapter(
    slug: str,
    n: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    return _run(svc.chapter_view, db, user, slug, n, locale)


@router.put("/{slug}/progress")
def save_position(
    slug: str,
    payload: PositionPayload,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The bookmark "Continue reading" returns to."""
    return _run(svc.save_position, db, user, slug, payload.chapter, payload.position)


@router.post("/{slug}/chapters/{n}/finish")
def finish_chapter(
    slug: str,
    n: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    return _run(svc.finish_chapter, db, user, slug, n, locale)


@router.post("/{slug}/listen")
def listened(
    slug: str,
    payload: ChapterPayload,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _run(svc.listened, db, user, slug, payload.chapter)


@router.post("/{slug}/lookup")
def looked_up(
    slug: str,
    payload: LookupPayload,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _run(svc.looked_up, db, user, slug, payload.word_id)


@router.post("/{slug}/explain")
def explain(
    slug: str,
    payload: ExplainPayload,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    """Help with a selection of a chapter: curriculum data always, an AI
    explanation only for focus explain/grammar (cached, offline-safe)."""
    return _run(svc.explain, db, user, slug, payload.chapter, payload.text, payload.focus, locale)


@journey_router.get("")
def my_journey(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Where the learner is, the one thing to do next, and the road ahead --
    all from their own records."""
    return journey_svc.journey(db, user)
