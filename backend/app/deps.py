from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.security import decode_access_token
from app.services.localization import SUPPORTED_LOCALES

bearer_scheme = HTTPBearer(auto_error=False)


def get_locale(x_locale: str | None = Header(default=None)) -> str:
    """The frontend sends its current i18next language on every request
    (see api.js) so responses can localize DB-driven content the same way
    the UI chrome already does. Anything not in SUPPORTED_LOCALES (English,
    missing header, unrecognized value) just means "use the original
    English column" -- routers never need to special-case "en" themselves."""
    if x_locale and x_locale.lower() in SUPPORTED_LOCALES:
        return x_locale.lower()
    return "en"


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
    user = db.get(models.User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


def require_admin(
    user: models.User = Depends(get_current_user),
) -> models.User:
    """Gate for every /api/admin/* route. Deny-by-default: composing on
    get_current_user means a missing/invalid token still 401s exactly as
    before, and any authenticated non-admin gets a 403 here — there is no
    code path that reaches an admin route on is_admin alone without also
    having passed real token verification first."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return user


def get_user_or_none(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User | None:
    if credentials is None:
        return None
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        return None
    return db.get(models.User, user_id)