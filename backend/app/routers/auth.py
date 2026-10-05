import logging
import re
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from google.auth import exceptions as google_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import get_db
from app.deps import get_client_ip
from app.security import (
    burn_password_check,
    create_access_token,
    hash_password,
    verify_password,
)
from app.services import login_throttle

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _find_by_email(db: Session, email: str) -> models.User | None:
    """Case-insensitive email lookup. Emails are stored as typed, so the same
    address can differ in letter case between a password registration and
    Google's normalized claim; an exact-case match is preferred, then the
    oldest case-insensitive match, so the result is always deterministic."""
    exact = db.query(models.User).filter(models.User.email == email).first()
    if exact is not None:
        return exact
    return (
        db.query(models.User)
        .filter(func.lower(models.User.email) == email.lower())
        .order_by(models.User.id)
        .first()
    )


def _is_admin_email(email: str) -> bool:
    return email.lower() in {e.strip().lower() for e in settings.admin_emails if e.strip()}


def _create_user_from_email(
    db: Session, email: str, display_name: str | None = None, google_sub: str | None = None
) -> models.User:
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
        google_sub=google_sub,
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
    if db.query(models.User).filter(
        func.lower(models.User.username) == payload.username.lower()
    ).first() is not None:
        raise HTTPException(status_code=409, detail="username already registered")
    if _find_by_email(db, payload.email) is not None:
        raise HTTPException(status_code=409, detail="email already registered")

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
def login(
    payload: schemas.LoginRequest,
    db: Session = Depends(get_db),
    ip: str | None = Depends(get_client_ip),
):
    # Checked before the password: while locked, even the right password is
    # refused, or the lock would just slow a guessing script down.
    wait = login_throttle.retry_after(payload.username, ip)
    if wait:
        raise HTTPException(
            status_code=429,
            detail=login_throttle.LOCKED_DETAIL,
            headers={"Retry-After": str(wait)},
        )
    user = (
        db.query(models.User)
        .filter(models.User.username == payload.username)
        .first()
    )
    if user is None:
        burn_password_check(payload.password)
    if user is None or not verify_password(payload.password, user.password_hash):
        login_throttle.record_failure(payload.username, ip)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated")
    login_throttle.record_success(payload.username, ip)
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
        # Covers a malformed, expired, tampered, or wrong-audience token. The
        # verifier's own text ("Token expired, 1759… < 1760…", "Wrong
        # recipient, payload audience != requested audience") used to be the
        # detail, so learners saw library internals; it goes to the log --
        # where a client-ID mismatch between frontend and backend is
        # diagnosed -- and the learner gets one stable sentence.
        logger.warning("Google credential rejected: %s", exc)
        raise HTTPException(
            status_code=401, detail="Google sign-in could not be verified"
        ) from exc
    except google_exceptions.GoogleAuthError as exc:
        # Covers transport/network failures reaching Google's cert endpoint —
        # not the token's fault, so it isn't a 401.
        logger.warning("Could not reach Google to verify a credential: %s", exc)
        raise HTTPException(
            status_code=503, detail="Could not reach Google to verify the sign-in"
        ) from exc

    email = claims.get("email")
    if not email or not claims.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google account has no verified email")
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Google credential has no account id")

    # Identity chain: Google `sub` (permanent) first, then the verified email
    # (links an existing password account or a pre-sub Google account), and
    # only then a brand-new row. Never a second account for the same person.
    user = db.query(models.User).filter(models.User.google_sub == sub).first()
    if user is None:
        user = _find_by_email(db, email)
        if user is not None:
            if user.google_sub and user.google_sub != sub:
                # The row is already bound to a different Google account;
                # silently re-binding it would hand one person's data to another.
                raise HTTPException(
                    status_code=409,
                    detail="This email is linked to a different Google account",
                )
            user.google_sub = sub
    if user is None:
        try:
            user = _create_user_from_email(
                db, email, display_name=claims.get("name"), google_sub=sub
            )
            db.flush()
        except IntegrityError:
            # Google's Identity Services widget can fire its callback twice
            # for one click, so two requests can both see "no user yet" and
            # race to insert the same email/sub. The loser falls back to the
            # row the winner just created.
            db.rollback()
            user = (
                db.query(models.User).filter(models.User.google_sub == sub).first()
                or _find_by_email(db, email)
            )
            if user is None:
                raise

    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated")
    # Admin comes only from the server-side allowlist, and only through a
    # Google-verified email -- never from anything the client sends.
    if _is_admin_email(email) and not user.is_admin:
        user.is_admin = True
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    return schemas.TokenResponse(access_token=token, user=user)
