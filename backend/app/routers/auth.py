import re
import secrets

from fastapi import APIRouter, Depends, HTTPException
from google.auth import exceptions as google_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import get_db
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _create_user_from_email(db: Session, email: str, display_name: str | None = None) -> models.User:
    # Prefer Google's display name for a friendlier username; fall back to
    # the email local-part if it's missing or sanitizes down to nothing.
    seed = re.sub(r"[^a-zA-Z0-9_]", "", (display_name or "").replace(" ", "_"))
    if len(seed) < 3:
        seed = re.sub(r"[^a-zA-Z0-9_]", "", email.split("@")[0])
    base_username = (seed or "user").lower()[:40]
    if len(base_username) < 3:
        base_username = f"user_{base_username}"[:40]
    username = base_username
    suffix = 1
    while db.query(models.User).filter(models.User.username == username).first() is not None:
        username = f"{base_username}{suffix}"
        suffix += 1

    user = models.User(
        username=username,
        email=email,
        # Google-authenticated accounts never use a password; store an
        # unguessable hash so the NOT NULL constraint and login-by-password
        # path both stay safe.
        password_hash=hash_password(secrets.token_urlsafe(32)),
    )
    db.add(user)
    db.flush()
    db.add(models.UserProfile(user_id=user.id))
    db.add(models.UserStreak(user_id=user.id))
    return user


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


@router.post("/google", response_model=schemas.TokenResponse)
def google_login(payload: schemas.GoogleAuthRequest, db: Session = Depends(get_db)):
    if not settings.google_client_id:
        raise HTTPException(
            status_code=501,
            detail=(
                "Google Sign-In is not configured on this server. "
                "Set GOOGLE_CLIENT_ID in backend/.env and restart the API."
            ),
        )
    try:
        # A fresh Request/session per call, not a long-lived module-level one:
        # a pooled keep-alive connection left idle between logins gets closed
        # server-side and the next reuse fails with a connection reset.
        claims = google_id_token.verify_oauth2_token(
            payload.credential, google_requests.Request(), settings.google_client_id
        )
    except ValueError as exc:
        # Covers a malformed, expired, tampered, or wrong-audience token.
        raise HTTPException(status_code=401, detail=f"Invalid Google credential: {exc}") from exc
    except google_exceptions.GoogleAuthError as exc:
        # Covers transport/network failures reaching Google's cert endpoint —
        # not the token's fault, so it isn't a 401.
        raise HTTPException(
            status_code=503, detail=f"Could not reach Google to verify the credential: {exc}"
        ) from exc

    email = claims.get("email")
    if not email or not claims.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google account has no verified email")

    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        try:
            user = _create_user_from_email(db, email, display_name=claims.get("name"))
            db.commit()
        except IntegrityError:
            # Google's Identity Services widget can fire its callback twice
            # for one click, so two requests can both see "no user yet" and
            # race to insert the same email. _create_user_from_email's own
            # flush() is where the unique-constraint hit lands; the loser
            # falls back to the row the winner just created.
            db.rollback()
            user = db.query(models.User).filter(models.User.email == email).first()
            if user is None:
                raise
    else:
        db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    return schemas.TokenResponse(access_token=token, user=user)