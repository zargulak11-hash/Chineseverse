from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud import apply_updates, get_or_404
from app.database import get_db
from app.security import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


def _ensure_animal_exists(db: Session, animal_id: int | None):
    if animal_id is not None and db.get(models.Animal, animal_id) is None:
        raise HTTPException(
            status_code=404, detail=f"Animal with id {animal_id} not found"
        )


def _check_unique(db: Session, payload, current_user=None):
    conflict = (
        db.query(models.User)
        .filter(
            or_(
                models.User.username == payload.username,
                models.User.email == payload.email,
            )
        )
        .first()
    )
    if conflict is not None and conflict.id != (current_user.id if current_user else -1):
        field = "username" if conflict.username == payload.username else "email"
        raise HTTPException(
            status_code=409, detail=f"{field} already registered"
        )


@router.get("", response_model=list[schemas.UserResponse])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).order_by(models.User.id).all()


@router.post("", response_model=schemas.UserResponse, status_code=201)
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    _ensure_animal_exists(db, payload.animal_id)
    _check_unique(db, payload)
    user = models.User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        animal_id=payload.animal_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=schemas.UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, models.User, user_id)


@router.put("/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: int, payload: schemas.UserUpdate, db: Session = Depends(get_db)
):
    user = get_or_404(db, models.User, user_id)
    _ensure_animal_exists(db, payload.animal_id)
    _check_unique(db, payload, current_user=user)
    user.username = payload.username
    user.email = payload.email
    if payload.password:
        user.password_hash = hash_password(payload.password)
    user.animal_id = payload.animal_id
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=schemas.UserResponse)
def patch_user(user_id: int, payload: schemas.UserPatch, db: Session = Depends(get_db)):
    user = get_or_404(db, models.User, user_id)
    data = payload.model_dump(exclude_unset=True)
    if "animal_id" in data:
        _ensure_animal_exists(db, data["animal_id"])
    if "username" in data or "email" in data:
        _check_unique(db, payload, current_user=user)
    if "password" in data and data["password"]:
        data["password_hash"] = hash_password(data["password"])
    data.pop("password", None)
    apply_updates(user, data)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = get_or_404(db, models.User, user_id)
    db.delete(user)
    db.commit()