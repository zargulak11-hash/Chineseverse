"""Detective Mode case files (services/detective.py).

Browsing only: a case is PLAYED as a server-graded practice round
(POST /api/practice/sessions {source: "detective", case})."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user
from app.services import detective as svc

router = APIRouter(prefix="/api/detective", tags=["detective"])


@router.get("/cases")
def cases(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.case_list(db, user)
