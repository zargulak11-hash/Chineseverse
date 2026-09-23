from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud import apply_updates, commit_or_409, get_or_404
from app.database import get_db
from app.services.activity import log_activity

router = APIRouter(prefix="/api/progress", tags=["progress"])


def _validate_refs(db: Session, user_id: int, lesson_id: int):
    if db.get(models.User, user_id) is None:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")
    if db.get(models.Lesson, lesson_id) is None:
        raise HTTPException(
            status_code=404, detail=f"Lesson with id {lesson_id} not found"
        )


def _sync_completed_at(item: models.Progress):
    if item.status == "completed" and item.completed_at is None:
        item.completed_at = datetime.utcnow()
    if item.status != "completed":
        item.completed_at = None


@router.get("", response_model=list[schemas.ProgressResponse])
def list_progress(
    user_id: int | None = None,
    lesson_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Progress)
    if user_id is not None:
        query = query.filter(models.Progress.user_id == user_id)
    if lesson_id is not None:
        query = query.filter(models.Progress.lesson_id == lesson_id)
    return query.order_by(models.Progress.id).all()


@router.get("/user/{user_id}", response_model=list[schemas.ProgressResponse])
def list_user_progress(user_id: int, db: Session = Depends(get_db)):
    get_or_404(db, models.User, user_id)
    return (
        db.query(models.Progress)
        .filter(models.Progress.user_id == user_id)
        .order_by(models.Progress.id)
        .all()
    )


@router.post("", response_model=schemas.ProgressResponse, status_code=201)
def create_progress(payload: schemas.ProgressCreate, db: Session = Depends(get_db)):
    _validate_refs(db, payload.user_id, payload.lesson_id)
    item = models.Progress(**payload.model_dump())
    _sync_completed_at(item)
    db.add(item)
    if item.status == "completed":
        user = db.get(models.User, item.user_id)
        if user:
            log_activity(db, user, "lesson_complete")
    commit_or_409(db, "Progress already exists for this user and lesson")
    db.refresh(item)
    return item


@router.get("/{progress_id}", response_model=schemas.ProgressResponse)
def get_progress(progress_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, models.Progress, progress_id)


def _log_if_newly_completed(db: Session, item: models.Progress, was_completed: bool) -> None:
    if item.status == "completed" and not was_completed:
        user = db.get(models.User, item.user_id)
        if user:
            log_activity(db, user, "lesson_complete")


@router.put("/{progress_id}", response_model=schemas.ProgressResponse)
def update_progress(
    progress_id: int, payload: schemas.ProgressUpdate, db: Session = Depends(get_db)
):
    item = get_or_404(db, models.Progress, progress_id)
    was_completed = item.status == "completed"
    item.status = payload.status
    item.score = payload.score
    _sync_completed_at(item)
    _log_if_newly_completed(db, item, was_completed)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{progress_id}", response_model=schemas.ProgressResponse)
def patch_progress(
    progress_id: int, payload: schemas.ProgressPatch, db: Session = Depends(get_db)
):
    item = get_or_404(db, models.Progress, progress_id)
    was_completed = item.status == "completed"
    apply_updates(item, payload.model_dump(exclude_unset=True))
    _sync_completed_at(item)
    _log_if_newly_completed(db, item, was_completed)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{progress_id}", status_code=204)
def delete_progress(progress_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, models.Progress, progress_id)
    db.delete(item)
    db.commit()