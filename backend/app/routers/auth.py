from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=schemas.TokenResponse, status_code=201)
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    existing = (
        db.query(models.User)
        .filter(
            (models.User.username == payload.username)
            | (models.User.email == payload.email)
        )
        .first()
    )
    if existing is not None:
        field = "username" if existing.username == payload.username else "email"
        raise HTTPException(status_code=409, detail=f"{field} already registered")

    user = models.User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()

    profile = db.query(models.UserProfile).filter_by(user_id=user.id).first()
    if profile is None:
        db.add(
            models.UserProfile(
                user_id=user.id,
                native_language=payload.native_language,
                daily_goal_minutes=payload.daily_goal_minutes,
            )
        )
    streak = db.query(models.UserStreak).filter_by(user_id=user.id).first()
    if streak is None:
        db.add(models.UserStreak(user_id=user.id))

    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    return schemas.TokenResponse(access_token=token, user=user)


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(models.User)
        .filter(models.User.username == payload.username)
        .first()
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(user.id)
    return schemas.TokenResponse(access_token=token, user=user)