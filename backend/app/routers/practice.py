from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services import lesson_path
from app.services import practice as svc
from app.services.companion_reaction import review_clear_reaction
from app.services.gamification import check_achievements

router = APIRouter(prefix="/api/practice", tags=["practice"])


class SessionCreate(BaseModel):
    source: str = Field(max_length=20)
    hsk_level: int | None = Field(default=None, ge=1, le=9)
    lesson_id: int | None = None
    size: int = Field(default=10, ge=4, le=20)
    # source "scene": a Real Chinese scene slug; source "sentence": the
    # Chinese sentence to turn into a lesson (validated by the server).
    scene: str | None = Field(default=None, max_length=40)
    sentence: str | None = Field(default=None, max_length=80)
    # source "detective": the case structure; source "sound": the place and
    # the speed stage (refused unless the learner has unlocked it).
    case: str | None = Field(default=None, max_length=30)
    env: str | None = Field(default=None, max_length=30)
    stage: int | None = Field(default=None, ge=1, le=4)


class SpeakPayload(BaseModel):
    index: int = Field(ge=0)
    spoken_text: str = Field(min_length=1, max_length=200)
    response_ms: int = Field(default=0, ge=0, le=600_000)


class AnswerPayload(BaseModel):
    index: int = Field(ge=0)
    choice_id: int
    response_ms: int = Field(default=0, ge=0, le=600_000)


def _owned(db: Session, session_id: int, user: models.User) -> models.PracticeSession:
    s = db.get(models.PracticeSession, session_id)
    if s is None or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Practice session not found")
    return s


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except svc.PracticeError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc


@router.post("/sessions", status_code=201)
def create_session(
    payload: SessionCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    if payload.source == "lesson" and payload.lesson_id is not None:
        # A lesson round is how a lesson gets completed, so it is only built
        # for a lesson the learner has reached on the path (admins included).
        state = lesson_path.path_state(db, user)
        if state.entry(payload.lesson_id) is not None and not state.is_open(payload.lesson_id):
            return JSONResponse(status_code=403, content=lesson_path.locked_payload(state))
    session = _run(
        svc.build_session, db, user, payload.source,
        hsk_level=payload.hsk_level, lesson_id=payload.lesson_id, size=payload.size, locale=locale,
        scene=payload.scene, sentence=payload.sentence,
        case=payload.case, env=payload.env, stage=payload.stage,
    )
    if session is None:
        # Review with nothing due: a real, successful "all caught up" state.
        return JSONResponse(status_code=200, content={
            "id": None, "source": payload.source, "questions": [], "empty": "nothing_due",
            "reaction": review_clear_reaction(user),
        })
    out = svc.render_session(db, session, locale)
    # Only a freshly started round greets the learner; GET re-renders don't.
    out["reaction"] = svc.start_reaction(db, user, session, locale)
    return out


@router.get("/sessions/{session_id}")
def get_session(
    session_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    return svc.render_session(db, _owned(db, session_id, user), locale)


@router.post("/sessions/{session_id}/answer")
def answer(
    session_id: int,
    payload: AnswerPayload,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    session = _owned(db, session_id, user)
    result = _run(svc.answer_question, db, user, session, payload.index, payload.choice_id, payload.response_ms, locale)
    check_achievements(db, user)
    return result


@router.post("/sessions/{session_id}/speak")
def speak(
    session_id: int,
    payload: SpeakPayload,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Say an answered scene reply / sentence aloud; graded against the
    stored question's own text (services/practice.speak)."""
    session = _owned(db, session_id, user)
    result = _run(svc.speak, db, user, session, payload.index, payload.spoken_text, payload.response_ms)
    check_achievements(db, user)
    return result


@router.post("/sessions/{session_id}/complete")
def complete(
    session_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    session = _owned(db, session_id, user)
    result = _run(svc.complete_session, db, user, session, locale)
    check_achievements(db, user)
    return result


@router.get("/review/summary")
def review_summary(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.review_counts(db, user)
