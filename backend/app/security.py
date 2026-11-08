import calendar
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings

def hash_password(password: str) -> str:
    # Read per call, not at import: the test suite lowers it after import.
    iterations = settings.password_hash_iterations
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def _stored_iterations(stored: str) -> int | None:
    try:
        return int(stored.split("$")[1])
    except (IndexError, ValueError, AttributeError):
        return None


def needs_rehash(stored: str) -> bool:
    """True for a hash made with fewer rounds than new hashes get (one from
    before the count was raised). Login re-hashes it with the password it
    has just verified -- the only moment the plain password is known."""
    iterations = _stored_iterations(stored)
    return iterations is not None and iterations < settings.password_hash_iterations


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, expected = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            int(iterations),
        ).hex()
        # Constant-time: `==` stops at the first differing character.
        return hmac.compare_digest(digest, expected)
    except (ValueError, AttributeError):
        return False


def burn_password_check(password: str, already_spent: str | None = None) -> None:
    """PBKDF2 work at the current cost, so an unknown username costs the
    same as a wrong password -- otherwise the response time alone says which
    usernames exist. `already_spent` is the stored hash a wrong password was
    just checked against: an older, cheaper hash is topped up to the
    current cost, or a not-yet-upgraded account would answer faster than a
    missing one. The result is never used."""
    target = settings.password_hash_iterations
    spent = _stored_iterations(already_spent) if already_spent is not None else 0
    remaining = target - (spent or 0)
    if remaining > 0:
        hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), os.urandom(16), remaining)


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _ticket_key() -> str:
    # Its own key, derived from the JWT secret: a sign-in ticket is then not
    # a validly signed access token (decode_access_token checks the plain
    # secret), so the short hand-off credential can never be used as a
    # session, and an access token can never be replayed as a ticket.
    return hmac.new(
        settings.jwt_secret.encode("utf-8"), b"oauth-sign-in-ticket", hashlib.sha256
    ).hexdigest()


def create_sign_in_ticket(user_id: int, ttl_seconds: int = 120) -> str:
    """A short-lived proof that the backend just finished an OAuth sign-in
    for `user_id`, carried from the provider callback to the SPA in an
    HttpOnly cookie and swapped once for a normal access token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "purpose": "oauth_sign_in",
        "iat": now,
        "exp": now + timedelta(seconds=ttl_seconds),
    }
    return jwt.encode(payload, _ticket_key(), algorithm="HS256")


def decode_sign_in_ticket(ticket: str) -> int | None:
    try:
        payload = jwt.decode(ticket, _ticket_key(), algorithms=["HS256"])
        if payload.get("purpose") != "oauth_sign_in":
            return None
        return int(payload.get("sub"))
    except (jwt.PyJWTError, TypeError, ValueError):
        return None


def decode_access_claims(token: str) -> tuple[int, int | None] | None:
    """(user id, issued-at in whole epoch seconds) of a valid access token,
    else None. The issue time is what lets a password change end the
    sessions opened before it (see token_predates_password_change)."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        iat = payload.get("iat")
        return int(payload.get("sub")), (int(iat) if iat is not None else None)
    # A validly signed token without a numeric "sub" is still not a session:
    # a 401, not an unhandled TypeError (500).
    except (jwt.PyJWTError, TypeError, ValueError):
        return None


def decode_access_token(token: str) -> int | None:
    claims = decode_access_claims(token)
    return claims[0] if claims else None


def token_predates_password_change(issued_at: int | None, changed_at: datetime | None) -> bool:
    """True for a token issued before the account's last password change.
    Both sides are whole seconds (PyJWT truncates `iat`; the change time is
    stored truncated), so the token handed out right after the change --
    in the same second -- still counts as issued after it."""
    if changed_at is None:
        return False
    if issued_at is None:
        return True
    return issued_at < calendar.timegm(changed_at.timetuple())