import ipaddress

from fastapi import Depends, HTTPException, Header, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.database import get_db
from app.security import decode_access_token
from app.services.localization import SUPPORTED_LOCALES, base_locale

bearer_scheme = HTTPBearer(auto_error=False)


def get_locale(x_locale: str | None = Header(default=None)) -> str:
    """The frontend sends its current i18next language on every request
    (see api.js) so responses can localize DB-driven content the same way
    the UI chrome already does. Anything not in SUPPORTED_LOCALES (English,
    missing header, unrecognized value) just means "use the original
    English column" -- routers never need to special-case "en" themselves."""
    loc = base_locale(x_locale)  # "ru-RU" from a browser-detected language counts as "ru"
    return loc if loc in SUPPORTED_LOCALES else "en"


def get_client_ip(request: Request) -> str | None:
    """The learner's address as the last trusted proxy saw it.

    Behind nginx the TCP peer is always the proxy, so the real address is
    in X-Forwarded-For -- but its leftmost entries are whatever the client
    chose to send. Each trusted proxy appends the address it received the
    request from, so the client is exactly `trusted_proxy_hops` entries in
    from the right of [forwarded..., peer]; anything further left is
    ignored. A chain shorter than that (a proxy that doesn't append) falls
    back to its leftmost entry, all of which came from trusted hops. None
    when nothing parses as an IP address."""
    hops = max(0, settings.trusted_proxy_hops)
    chain: list[str] = []
    if hops:
        for header in request.headers.getlist("x-forwarded-for"):
            chain.extend(part.strip() for part in header.split(",") if part.strip())
    if request.client and request.client.host:
        chain.append(request.client.host)
    if not chain:
        return None
    candidate = chain[-(hops + 1)] if len(chain) > hops else chain[0]
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


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
    user = db.get(models.User, user_id)
    # A deactivated account is anonymous here too, as get_current_user
    # refuses it: its still-unexpired token must not keep an admin's view
    # of lesson bodies or a learner's unlocks.
    if user is None or not user.is_active:
        return None
    return user