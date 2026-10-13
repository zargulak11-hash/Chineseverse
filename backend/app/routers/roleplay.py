from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services import roleplay as svc
from app.services.gamification import check_achievements

router = APIRouter(prefix="/api/roleplay", tags=["roleplay"])


class StartPayload(BaseModel):
    scenario: str = Field(min_length=1, max_length=40)


class TurnPayload(BaseModel):
    # Length is checked by the service too, with a human-readable detail.
    text: str = Field(min_length=1, max_length=400)


def _run(fn, *args):
    try:
        return fn(*args)
    except svc.RoleplayError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc


@router.get("/scenarios")
def scenarios(user: models.User = Depends(get_current_user), db: Session = Depends(get_db),
              locale: str = Depends(get_locale)):
    return svc.scenario_list(db, user, locale)


@router.get("/sessions")
def recent(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The learner's last conversations (to continue one or reread its summary)."""
    rows = (db.query(models.RoleplaySession).filter_by(user_id=user.id)
            .order_by(models.RoleplaySession.created_at.desc()).limit(10).all())
    return [{"id": r.id, "scenario": r.scenario, "status": r.status, "created_at": r.created_at.isoformat(),
             "messages": sum(1 for t in r.turns or [] if t["role"] == "learner")} for r in rows]


@router.post("/sessions", status_code=201)
def start(payload: StartPayload, user: models.User = Depends(get_current_user), db: Session = Depends(get_db),
          locale: str = Depends(get_locale)):
    session = _run(svc.start, db, user, payload.scenario, locale)
    return svc.render(db, session, locale)


@router.get("/sessions/{session_id}")
def get_session(session_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db),
                locale: str = Depends(get_locale)):
    return svc.render(db, _run(svc._own, db, user, session_id), locale)


@router.post("/sessions/{session_id}/turn")
def turn(session_id: int, payload: TurnPayload, user: models.User = Depends(get_current_user),
         db: Session = Depends(get_db), locale: str = Depends(get_locale)):
    session = _run(svc._own, db, user, session_id)
    out = _run(svc.turn, db, user, session, payload.text, locale)
    check_achievements(db, user)
    return out


@router.post("/sessions/{session_id}/hint")
def hint(session_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db),
         locale: str = Depends(get_locale)):
    return _run(svc.hint, db, user, _run(svc._own, db, user, session_id), locale)


@router.post("/sessions/{session_id}/finish")
def finish(session_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db),
           locale: str = Depends(get_locale)):
    session = _run(svc._own, db, user, session_id)
    out = _run(svc.finish, db, user, session, locale)
    check_achievements(db, user)
    return out
