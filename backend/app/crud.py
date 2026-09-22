from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


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