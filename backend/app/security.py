import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings

PBKDF2_ITERATIONS = 100_000


def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


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


# Verified against when a login names no existing account, so an unknown
# username costs the same PBKDF2 work as a wrong password -- otherwise the
# response time alone says which usernames exist.
_DUMMY_HASH = hash_password(os.urandom(16).hex())


def burn_password_check(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


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


def decode_access_token(token: str) -> int | None:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return int(payload.get("sub"))
    # A validly signed token without a numeric "sub" is still not a session:
    # a 401, not an unhandled TypeError (500).
    except (jwt.PyJWTError, TypeError, ValueError):
        return None