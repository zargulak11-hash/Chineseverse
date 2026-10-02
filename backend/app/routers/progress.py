from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud import apply_updates, commit_or_409
from app.database import get_db
from app.deps import get_current_user
from app.services.activity import log_activity

router = APIRouter(prefix="/api/progress", tags=["progress"])

# Every route here is scoped to the signed-in user. These endpoints used to
# be fully public and unscoped: GET /api/progress returned every user's rows,
# and the Lessons pages picked the first row matching a lesson id -- so on a
# multi-user database a learner saw (and PATCHed) someone else's lesson
# progress. Admins may read another user's rows; nobody can write them.


def _own_or_404(db: Session, progress_id: int, user: models.User) -> models.Progress:
    item = db.get(models.Progress, progress_id)
    # 404 (not 403) for someone else's row, so ids don't leak existence.
    if item is None or item.user_id != user.id:
        raise HTTPException(status_code=404, detail=f"Progress with id {progress_id} not found")
    return item


def _no_self_completion(new_status: str | None, was_completed: bool = False) -> None:
    """A lesson is completed only by passing its server-graded practice round
    (services.practice._record_lesson), on the lesson path's order. These
    endpoints used to accept status="completed" from the client, which let a
    learner complete -- and so unlock past -- any lesson without doing it."""
    if new_status == "completed" and not was_completed:
        raise HTTPException(
            status_code=403,
            detail="Lessons are completed by passing their practice round",
        )


def _no_client_score(score: int | None, current: int | None = None) -> None:
    """A lesson's score is its best graded practice round, recorded by
    services.practice._record_lesson. These endpoints used to store any 0-100
    score the client sent, so a learner could show a perfect score on a
    lesson they never practiced. Re-sending the stored value is accepted."""
    if score is not None and score != current:
        raise HTTPException(
            status_code=403,
            detail="Lesson scores are recorded by graded practice",
        )


def _sync_completed_at(item: models.Progress):
    if item.status == "completed" and item.completed_at is None:
        item.completed_at = datetime.utcnow()
    if item.status != "completed":
        item.completed_at = None


@router.get("", response_model=list[schemas.ProgressResponse])
def list_progress(
    lesson_id: int | None = None,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.Progress).filter(models.Progress.user_id == user.id)
    if lesson_id is not None:
        query = query.filter(models.Progress.lesson_id == lesson_id)
    return query.order_by(models.Progress.id).all()


@router.get("/user/{user_id}", response_model=list[schemas.ProgressResponse])
def list_user_progress(
    user_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="You can only view your own progress")
    if db.get(models.User, user_id) is None:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")
    return (
        db.query(models.Progress)
        .filter(models.Progress.user_id == user_id)
        .order_by(models.Progress.id)
        .all()
    )


@router.post("", response_model=schemas.ProgressResponse, status_code=201)
def create_progress(
    payload: schemas.ProgressCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.user_id is not None and payload.user_id != user.id:
        raise HTTPException(status_code=403, detail="You can only record your own progress")
    if db.get(models.Lesson, payload.lesson_id) is None:
        raise HTTPException(status_code=404, detail=f"Lesson with id {payload.lesson_id} not found")
    _no_self_completion(payload.status)
    _no_client_score(payload.score)
    item = models.Progress(user_id=user.id, lesson_id=payload.lesson_id, status=payload.status)
    _sync_completed_at(item)
    db.add(item)
    if item.status == "completed":
        log_activity(db, user, "lesson_complete")
    commit_or_409(db, "Progress already exists for this user and lesson")
    db.refresh(item)
    return item


@router.get("/{progress_id}", response_model=schemas.ProgressResponse)
def get_progress(
    progress_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _own_or_404(db, progress_id, user)


def _log_if_newly_completed(db: Session, user: models.User, item: models.Progress, was_completed: bool) -> None:
    if item.status == "completed" and not was_completed:
        log_activity(db, user, "lesson_complete")


@router.put("/{progress_id}", response_model=schemas.ProgressResponse)
def update_progress(
    progress_id: int,
    payload: schemas.ProgressUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _own_or_404(db, progress_id, user)
    was_completed = item.status == "completed"
    _no_self_completion(payload.status, was_completed)
    _no_client_score(payload.score, item.score)
    item.status = payload.status
    _sync_completed_at(item)
    _log_if_newly_completed(db, user, item, was_completed)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{progress_id}", response_model=schemas.ProgressResponse)
def patch_progress(
    progress_id: int,
    payload: schemas.ProgressPatch,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _own_or_404(db, progress_id, user)
    was_completed = item.status == "completed"
    _no_self_completion(payload.status, was_completed)
    _no_client_score(payload.score, item.score)
    apply_updates(item, payload.model_dump(exclude_unset=True, exclude={"score"}))
    _sync_completed_at(item)
    _log_if_newly_completed(db, user, item, was_completed)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{progress_id}", status_code=204)
def delete_progress(
    progress_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _own_or_404(db, progress_id, user)
    db.delete(item)
    db.commit()
