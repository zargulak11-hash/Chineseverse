"""One Sentence -> Complete Lesson (services/sentence.py).

/analyze only reads: it breaks a sentence into the curriculum's own words,
characters and grammar for this learner. The lesson's graded activities
are a practice round (POST /api/practice/sessions {source: "sentence",
sentence}), so grading and progress stay on the server."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user, get_locale
from app.services import sentence as svc

router = APIRouter(prefix="/api/sentence", tags=["sentence"])


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=80)


@router.post("/analyze")
def analyze(
    payload: AnalyzeRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    try:
        return svc.analyze(db, user, payload.text, locale)
    except svc.SentenceError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc


@router.get("/suggestions")
def suggestions(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    locale: str = Depends(get_locale),
):
    return {"suggestions": svc.suggestions(db, user, locale)}
