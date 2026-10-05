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