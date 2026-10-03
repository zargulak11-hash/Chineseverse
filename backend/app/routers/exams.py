"""/api/exams -- HSK level final exams (rules in services/hsk_exam.py).

Every route authenticates; an attempt is only ever resolved for its own
user (404 for anyone else's). The client sends option ids and integrity
reports -- never a score, a pass flag or a status; extra fields in a body
are ignored.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services import hsk_exam as svc
from app.services.gamification import check_achievements

router = APIRouter(prefix="/api/exams", tags=["exams"])


class AnswerPayload(BaseModel):
    index: int = Field(ge=0)
    choice_id: int


class ViolationPayload(BaseModel):
    reason: str = Field(max_length=20)


def _owned(db: Session, attempt_id: int, user: models.User) -> models.HSKExamAttempt:
    attempt = db.get(models.HSKExamAttempt, attempt_id)
    if attempt is None or attempt.user_id != user.id:
        raise HTTPException(status_code=404, detail="Exam attempt not found")
    return attempt


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except svc.ExamError as exc:
        return JSONResponse(status_code=exc.status, content={"detail": exc.detail, "code": exc.code, **exc.extra})


@router.get("")
def exams_overview(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.overview(db, user)


@router.post("/{level}/start", status_code=201)
def start_exam(
    level: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    if not 1 <= level <= 9:
        raise HTTPException(status_code=404, detail="No such HSK level")
    attempt = _run(svc.start, db, user, level, locale)
    if isinstance(attempt, JSONResponse):
        return attempt
    return svc.render(db, attempt, locale)


@router.get("/attempts/{attempt_id}")
def get_attempt(attempt_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The result of an attempt. Opening an attempt that is still in
    progress -- a reload, a second tab, a pasted URL -- ends it: an exam is
    taken in one sitting, on the page that started it."""
    attempt = _owned(db, attempt_id, user)
    svc.expire_stale(db, user)
    db.refresh(attempt)
    if attempt.status == svc.IN_PROGRESS:
        return svc.violate(db, attempt, "reopened")
    return svc.result(attempt)


@router.post("/attempts/{attempt_id}/answer")
def answer(
    attempt_id: int,
    payload: AnswerPayload,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _run(svc.answer, db, _owned(db, attempt_id, user), payload.index, payload.choice_id)


@router.post("/attempts/{attempt_id}/submit")
def submit(attempt_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = _run(svc.submit, db, _owned(db, attempt_id, user))
    check_achievements(db, user)  # a passed exam is an HSK milestone
    return result


@router.post("/attempts/{attempt_id}/heartbeat")
def heartbeat(attempt_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The exam page is still open, visible and focused."""
    return _run(svc.heartbeat, db, _owned(db, attempt_id, user))


@router.post("/attempts/{attempt_id}/violation")
def violation(
    attempt_id: int,
    payload: ViolationPayload,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reason = payload.reason if payload.reason in svc.VIOLATIONS else "left_page"
    return svc.violate(db, _owned(db, attempt_id, user), reason)
