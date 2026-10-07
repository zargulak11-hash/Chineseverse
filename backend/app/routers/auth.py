import logging
import re
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
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
    create_sign_in_ticket,
    decode_sign_in_ticket,
    hash_password,
    verify_password,
)
from app.services import github_oauth, login_throttle

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
    db: Session,
    email: str,
    display_name: str | None = None,
    google_sub: str | None = None,
    github_id: str | None = None,
) -> models.User:
    # Prefer the provider's display name for a friendlier username; fall back
    # to the email local-part if it's missing or sanitizes down to nothing.
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
        github_id=github_id,
        # Provider-created accounts never use a password; store an
        # unguessable hash so the NOT NULL constraint and login-by-password
        # path both stay safe.
        password_hash=hash_password(secrets.token_urlsafe(32)),
    )
    db.add(user)
    db.flush()
    db.add(models.UserProfile(user_id=user.id))
    db.add(models.UserStreak(user_id=user.id))
    return user


def _sign_in_external(
    db: Session,
    *,
    id_field: str,
    provider_id: str,
    email: str,
    display_name: str | None,
    conflict_detail: str,
) -> models.User:
    """The identity chain every external sign-in shares (Google, GitHub):
    the provider's permanent account id first, then the provider-VERIFIED
    email (links an existing password account, or a provider account from
    before linking existed), and only then a brand-new row. Never a second
    account for the same person. Flushes, does not commit."""
    column = getattr(models.User, id_field)
    user = db.query(models.User).filter(column == provider_id).first()
    if user is None:
        user = _find_by_email(db, email)
        if user is not None:
            linked = getattr(user, id_field)
            if linked and linked != provider_id:
                # The row is already bound to a different account at this
                # provider; silently re-binding it would hand one person's
                # data to another.
                raise HTTPException(status_code=409, detail=conflict_detail)
            setattr(user, id_field, provider_id)
    if user is None:
        try:
            user = _create_user_from_email(
                db, email, display_name=display_name, **{id_field: provider_id}
            )
            db.flush()
        except IntegrityError:
            # Two requests for one sign-in (Google's widget can fire its
            # callback twice; a double-clicked button) can both see "no user
            # yet" and race to insert the same email/id. The loser falls back
            # to the row the winner just created.
            db.rollback()
            user = (
                db.query(models.User).filter(column == provider_id).first()
                or _find_by_email(db, email)
            )
            if user is None:
                raise
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated")
    return user


@router.get("/providers")
def providers():
    """Which external sign-ins this server can complete, so the Login and
    Register pages show a working button or say it isn't set up -- never a
    button that fails after a round trip to the provider. Booleans only."""
    return {
        "google": bool(settings.google_client_id),
        "github": github_oauth.is_configured(),
    }


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

    user = _sign_in_external(
        db,
        id_field="google_sub",
        provider_id=sub,
        email=email,
        display_name=claims.get("name"),
        conflict_detail="This email is linked to a different Google account",
    )
    # Admin comes only from the server-side allowlist, and only through a
    # Google-verified email -- never from anything the client sends. (GitHub
    # sign-in deliberately does not consult the list: admin stays tied to
    # the one provider it was granted through.)
    if _is_admin_email(email) and not user.is_admin:
        user.is_admin = True
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    return schemas.TokenResponse(access_token=token, user=user)


# --------------------------------------------------------------------------
# GitHub sign-in: a full-page redirect flow, not a popup. GitHub's authorize
# page is left with a plain top-level navigation and comes back the same
# way, so there is no popup to block, no window.opener and no third-party
# cookie involved -- the two cookies below are first-party, SameSite=Lax
# (sent on the top-level GET back from github.com in every current
# browser), HttpOnly, and scoped to /api/auth/github.
#
#   /start     state -> cookie, then 302 to GitHub
#   /callback  state checked, code exchanged server-side, account resolved,
#              short sign-in ticket -> cookie, then 302 to the SPA's
#              /auth/github page
#   /session   the SPA swaps the ticket cookie (once) for the normal
#              access token
#
# The access token is never put in a URL, so it can't land in browser
# history, a Referer header or an access log. Every failure returns to the
# page the learner started from with ?auth_error=<code>, which the frontend
# translates.
# --------------------------------------------------------------------------

STATE_COOKIE = "cv_github_state"
TICKET_COOKIE = "cv_github_ticket"
GITHUB_COOKIE_PATH = "/api/auth/github"
STATE_TTL_SECONDS = 600
TICKET_TTL_SECONDS = 120
# Where a flow may return to: a fixed list, so the round trip can't be
# turned into an open redirect.
RETURN_PAGES = {"login", "register"}


def _cookie_secure() -> bool:
    # The API itself is reached over plain HTTP behind nginx, so the
    # request's own scheme can't tell; the public callback URL can.
    return github_oauth.redirect_uri().startswith("https://")


def _set_flow_cookie(response: Response, name: str, value: str, max_age: int) -> None:
    response.set_cookie(
        name,
        value,
        max_age=max_age,
        path=GITHUB_COOKIE_PATH,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
    )


def _clear_flow_cookie(response: Response, name: str) -> None:
    response.delete_cookie(
        name, path=GITHUB_COOKIE_PATH, httponly=True, secure=_cookie_secure(), samesite="lax"
    )


def _no_store(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store"
    return response


def _back_with_error(page: str, code: str) -> RedirectResponse:
    response = RedirectResponse(f"/{page}?auth_error={code}", status_code=302)
    _clear_flow_cookie(response, STATE_COOKIE)
    return _no_store(response)


@router.get("/github/start")
def github_start(page: str = "login"):
    page = page if page in RETURN_PAGES else "login"
    if not github_oauth.is_configured():
        return _back_with_error(page, "github_not_configured")
    state = secrets.token_urlsafe(32)
    response = RedirectResponse(github_oauth.authorize_url(state), status_code=302)
    # The page rides along with the state so the callback knows where to
    # send the learner back; it is only ever one of RETURN_PAGES.
    _set_flow_cookie(response, STATE_COOKIE, f"{state}.{page}", STATE_TTL_SECONDS)
    return _no_store(response)


@router.get("/github/callback")
def github_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    stored = request.cookies.get(STATE_COOKIE) or ""
    expected_state, _, page = stored.partition(".")
    page = page if page in RETURN_PAGES else "login"

    if error:
        # access_denied = the learner pressed Cancel on GitHub's page.
        return _back_with_error(page, "github_cancelled" if error == "access_denied" else "github_failed")
    # CSRF guard: the state GitHub hands back must be the one this browser
    # was given at /start. Missing cookie (expired, another browser, the
    # callback opened a second time) or a mismatch never signs anyone in.
    if not expected_state or not state or not secrets.compare_digest(expected_state, state):
        return _back_with_error(page, "github_state")
    if not code:
        return _back_with_error(page, "github_failed")
    if not github_oauth.is_configured():
        return _back_with_error(page, "github_not_configured")

    try:
        identity = github_oauth.fetch_identity(github_oauth.exchange_code(code))
    except github_oauth.GitHubAuthError as exc:
        logger.warning("GitHub sign-in failed (%s): %s", exc.code, exc)
        return _back_with_error(page, exc.code)

    try:
        user = _sign_in_external(
            db,
            id_field="github_id",
            provider_id=identity.id,
            email=identity.email,
            display_name=identity.name or identity.login,
            conflict_detail="This email is linked to a different GitHub account",
        )
    except HTTPException as exc:
        db.rollback()
        return _back_with_error(page, "github_other_account" if exc.status_code == 409 else "deactivated")
    db.commit()
    logger.info("GitHub sign-in completed for user %s", user.id)

    response = RedirectResponse("/auth/github", status_code=302)
    _clear_flow_cookie(response, STATE_COOKIE)
    _set_flow_cookie(response, TICKET_COOKIE, create_sign_in_ticket(user.id, TICKET_TTL_SECONDS), TICKET_TTL_SECONDS)
    return _no_store(response)


@router.post("/github/session", response_model=schemas.TokenResponse)
def github_session(request: Request, response: Response, db: Session = Depends(get_db)):
    """Swap the callback's sign-in ticket for an access token. The cookie is
    cleared by the same response, so a ticket works once; a second call
    (a refreshed /auth/github page) gets a 401 the page handles."""
    _clear_flow_cookie(response, TICKET_COOKIE)
    _no_store(response)
    user_id = decode_sign_in_ticket(request.cookies.get(TICKET_COOKIE) or "")
    user = db.get(models.User, user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(status_code=401, detail="This GitHub sign-in has expired. Please try again.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated")
    token = create_access_token(user.id)
    return schemas.TokenResponse(access_token=token, user=user)
