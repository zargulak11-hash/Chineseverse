from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models


def get_or_404(db: Session, model, item_id: int):
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(
            status_code=404, detail=f"{model.__name__} with id {item_id} not found"
        )
    return item


def apply_updates(item, data: dict):
    for key, value in data.items():
        setattr(item, key, value)
    return item


def commit_or_409(db: Session, message: str) -> None:
    """Commit the session, translating a unique/FK violation into a 409.

    Shared by every router that creates or updates a uniquely-constrained
    row, instead of each one repeating its own try/except IntegrityError.
    """
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=message)


def delete_user_cascade_safe(db: Session, user: "models.User") -> None:
    """Delete a User row without leaving broken foreign keys behind.

    Most user-owned tables cascade automatically via User's own
    cascade="all, delete-orphan" relationships. The tables below are the
    exceptions: plain FK columns with no relationship declared on User and
    no ondelete= at the DB level, so a bare db.delete(user) raises
    ForeignKeyViolation for any user these actually apply to. Confirmed the
    hard way: PlacementAttempt/ActivityEvent weren't caught by the original
    Follow/Duel audit because the accounts tested against at the time were
    freshly created and had no onboarding/activity history yet to expose
    the gap — a bulk cleanup of real accounts with real history hit it
    immediately.

    - Follow.follower_id/following_id: deleted outright (nothing meaningful
      to keep once one side of a follow relationship is gone).
    - Duel.winner_id: nulled, not deleted — the duel record and the other
      participant's history survive; only the dangling reference is cleared.
    - PlacementAttempt/ActivityEvent: deleted outright — both are pure
      per-user history rows (onboarding placement test, activity log) with
      no meaning to anyone but this user and nothing else in the schema
      references either table's id, so there's nothing to preserve.
    """
    db.query(models.Follow).filter(
        (models.Follow.follower_id == user.id) | (models.Follow.following_id == user.id)
    ).delete(synchronize_session=False)
    db.query(models.Duel).filter(models.Duel.winner_id == user.id).update(
        {models.Duel.winner_id: None}, synchronize_session=False
    )
    db.query(models.PlacementAttempt).filter(models.PlacementAttempt.user_id == user.id).delete(
        synchronize_session=False
    )
    db.query(models.ActivityEvent).filter(models.ActivityEvent.user_id == user.id).delete(
        synchronize_session=False
    )
    db.delete(user)
    db.commit()